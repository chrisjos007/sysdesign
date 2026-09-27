import random

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import quorum, ring, services
from .curriculum import DNS_TCP_TLS
from .context_processors import _chapter_href
from .models import (
    Attempt, Badge, Chapter, CodingChallenge, Concept, ConceptMastery, DesignChallenge,
    FlawChallenge, FlawPart, MatchingChallenge, OrderingChallenge, Question, QuorumChallenge,
    ReviewCard, RingChallenge, Topic, TrafficChallenge, UserBadge,
)
from .services import (
    all_flaws_found, answer_flaw_part, chapter_is_unlocked, due_review_cards, flaw_snapshot,
    get_profile, inspect_flaw_part, new_flaw_run, record_coding_attempt,
    record_design_attempt, record_flaw_attempt, record_matching_attempt,
    record_ordering_attempt, record_quiz_answer, record_quorum_attempt, record_ring_attempt,
    record_traffic_attempt,
)
import json


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('learn:dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


def _tiers_for_chapters(chapters, request, profile, with_pct=False):
    """Buckets a queryset of Chapter into difficulty tiers (Beginner/
    Intermediate/Advanced), dropping empty tiers, for topic-based display."""
    tiers_by_level = {level: [] for level, _ in Chapter.DIFFICULTY_CHOICES}
    for chapter in chapters:
        total = chapter.concepts.count()
        mastered = ConceptMastery.objects.filter(
            user=request.user, concept__chapter=chapter,
            state=ConceptMastery.STATE_MASTERED,
        ).count()
        entry = {
            'chapter': chapter,
            'unlocked': chapter_is_unlocked(chapter, profile),
            'total': total,
            'mastered': mastered,
            'href': _chapter_href(chapter),
        }
        if with_pct:
            entry['pct'] = int(100 * mastered / total) if total else 0
        tiers_by_level[chapter.difficulty].append(entry)
    return [
        {'label': label, 'chapters': tiers_by_level[level]}
        for level, label in Chapter.DIFFICULTY_CHOICES
        if tiers_by_level[level]
    ]


LEITNER_BOXES = [
    (1, 'New or missed'),
    (2, 'Recalled once'),
    (3, 'Recalled twice'),
    (4, 'Three in a row'),
    (5, 'Long-term'),
]


def _leitner_box(card):
    """Files a concept's review card into a Leitner compartment by its SM-2
    repetition streak: a wrong answer resets repetitions to 0, which is
    exactly Leitner's 'back to box 1'. Cards past four clean recalls all
    live in box 5."""
    return min(card.repetitions, 4) + 1


def _continue_concept(user, profile):
    """The card to reopen: the concept behind the learner's most recent quiz
    attempt, unless it's already mastered; otherwise the first unlocked,
    unmastered concept in drawer order."""
    mastered_ids = set(ConceptMastery.objects.filter(
        user=user, state=ConceptMastery.STATE_MASTERED).values_list('concept_id', flat=True))
    last = Attempt.objects.filter(user=user).select_related('question__concept__chapter__topic').first()
    if last and last.question.concept_id not in mastered_ids:
        return last.question.concept, True
    for concept in Concept.objects.select_related('chapter__topic').order_by(
            'chapter__topic__order', 'chapter__difficulty', 'chapter__order', 'order', 'id'):
        if concept.id not in mastered_ids and chapter_is_unlocked(concept.chapter, profile):
            return concept, False
    return None, False


@login_required
def dashboard(request):
    profile = get_profile(request.user)
    now = timezone.now()

    cards = {c.concept_id: c for c in ReviewCard.objects.filter(user=request.user)}
    boxes = {n: {'number': n, 'label': label, 'count': 0, 'due': 0} for n, label in LEITNER_BOXES}
    for card in cards.values():
        box = boxes[_leitner_box(card)]
        box['count'] += 1
        if card.due_at <= now:
            box['due'] += 1

    topics = Topic.objects.prefetch_related('chapters__concepts')
    topic_data = []
    unfiled = 0
    for topic in topics:
        tiers = _tiers_for_chapters(topic.chapters.all(), request, profile, with_pct=True)
        if not tiers:
            continue
        chapters = []
        for tier in tiers:
            for entry in tier['chapters']:
                # A chapter card is stamped with the lowest compartment any of
                # its concepts sits in: the weakest card sets the pace.
                chapter_cards = [cards[c.id] for c in entry['chapter'].concepts.all() if c.id in cards]
                entry['tier'] = tier['label']
                entry['box'] = min((_leitner_box(c) for c in chapter_cards), default=None)
                entry['due'] = any(c.due_at <= now for c in chapter_cards)
                if entry['box'] is None:
                    unfiled += 1
                chapters.append(entry)
        topic_data.append({
            'topic': topic,
            'chapters': chapters,
            'mastered': sum(e['mastered'] for e in chapters),
            'total': sum(e['total'] for e in chapters),
        })

    continue_concept, resumed = _continue_concept(request.user, profile)
    due_count = sum(b['due'] for b in boxes.values())
    filed_max = max([b['count'] for b in boxes.values()] + [1])

    return render(request, 'learn/dashboard.html', {
        'profile': profile,
        'topic_data': topic_data,
        'boxes': list(boxes.values()),
        'filed_total': len(cards),
        'filed_max': filed_max,
        'unfiled': unfiled,
        'due_count': due_count,
        'continue_concept': continue_concept,
        'continue_resumed': resumed,
        'due_concept_ids': {cid for cid, c in cards.items() if c.due_at <= now},
        'continue_activities': (
            1 + continue_concept.design_challenges.count() + continue_concept.matching_challenges.count()
            + continue_concept.ordering_challenges.count() + continue_concept.coding_challenges.count()
            + continue_concept.flaw_challenges.count() + continue_concept.traffic_challenges.count()
            + continue_concept.quorum_challenges.count() + continue_concept.ring_challenges.count()
        ) if continue_concept else 0,
    })


@login_required
def topic_detail(request, topic_slug):
    topic = get_object_or_404(Topic, slug=topic_slug)
    profile = get_profile(request.user)
    tiers = _tiers_for_chapters(topic.chapters.all(), request, profile)
    return render(request, 'learn/topic_detail.html', {'topic': topic, 'tiers': tiers})


@login_required
def chapter_detail(request, chapter_slug):
    chapter = get_object_or_404(Chapter, slug=chapter_slug)
    profile = get_profile(request.user)
    unlocked = chapter_is_unlocked(chapter, profile)
    concepts = []
    for concept in chapter.concepts.all():
        mastery = ConceptMastery.objects.filter(user=request.user, concept=concept).first()
        concepts.append({
            'concept': concept,
            'state': mastery.state if mastery else ConceptMastery.STATE_AVAILABLE,
        })
    return render(request, 'learn/chapter_detail.html', {
        'chapter': chapter, 'unlocked': unlocked, 'concepts': concepts,
    })


@login_required
def concept_detail(request, concept_slug):
    concept = get_object_or_404(Concept, slug=concept_slug)
    profile = get_profile(request.user)
    if not chapter_is_unlocked(concept.chapter, profile):
        messages.error(request, "This chapter is still locked. Keep leveling up!")
        return redirect('learn:dashboard')
    mastery = ConceptMastery.objects.filter(user=request.user, concept=concept).first()
    return render(request, 'learn/concept_detail.html', {
        'concept': concept,
        'mastery': mastery,
        'question_count': concept.questions.count(),
        'request_lesson': DNS_TCP_TLS if concept.slug == DNS_TCP_TLS['slug'] else None,
        'http_api_lesson': concept.slug == 'http-api-design',
        'design_challenges': concept.design_challenges.all(),
        'matching_challenges': concept.matching_challenges.all(),
        'ordering_challenges': concept.ordering_challenges.all(),
        'coding_challenges': concept.coding_challenges.all(),
        'flaw_challenges': concept.flaw_challenges.all(),
        'traffic_challenges': concept.traffic_challenges.all(),
        'quorum_challenges': concept.quorum_challenges.all(),
        'ring_challenges': concept.ring_challenges.all(),
    })


def _new_quiz_run(concept):
    """A fresh, shuffled run through every question in this concept's bank,
    exactly once each — this is what gives the quiz a definite end."""
    ids = list(concept.questions.values_list('id', flat=True))
    random.shuffle(ids)
    return {'order': ids, 'total': len(ids), 'answered': 0, 'correct': 0, 'xp_total': 0}


@login_required
def concept_quiz(request, concept_slug):
    concept = get_object_or_404(Concept, slug=concept_slug)
    profile = get_profile(request.user)
    if not chapter_is_unlocked(concept.chapter, profile):
        messages.error(request, "This chapter is still locked.")
        return redirect('learn:dashboard')

    session_key = f'quiz_run_{concept.id}'
    result = None

    if request.method == 'POST':
        run = request.session.get(session_key) or _new_quiz_run(concept)
        question = get_object_or_404(Question, id=request.POST.get('question_id'), concept=concept)
        selected_ids = [cid for cid in request.POST.getlist('choice_id') if cid.isdigit()]
        result = record_quiz_answer(request.user, question, selected_ids)
        result['question'] = question
        result['selected_choices'] = list(question.choices.filter(id__in=selected_ids))
        result['correct_choices'] = list(question.choices.filter(is_correct=True))

        if question.id in run['order']:
            run['order'].remove(question.id)
        run['answered'] += 1
        if result['is_correct']:
            run['correct'] += 1
        run['xp_total'] += result['xp_awarded']
        request.session[session_key] = run
        request.session.modified = True
    else:
        run = request.session.get(session_key)
        if request.GET.get('restart') == '1' or not run:
            run = _new_quiz_run(concept)
            request.session[session_key] = run

    empty = run['total'] == 0
    finished = not empty and not run['order']
    next_question = None
    choices = []
    if not empty and not finished:
        next_question = Question.objects.get(id=run['order'][0])
        choices = list(next_question.choices.all())
        random.shuffle(choices)

    # One tick per question in the run: answered, the one on screen, still to come.
    answered = run['answered']
    run_ticks = ['done'] * min(answered, run['total'])
    if not finished and not empty:
        run_ticks.append('current')
    run_ticks += ['todo'] * max(run['total'] - len(run_ticks), 0)

    return render(request, 'learn/quiz.html', {
        'concept': concept,
        'result': result,
        'next_question': next_question,
        'choices': choices,
        'run': run,
        'run_ticks': run_ticks,
        'empty': empty,
        'finished': finished,
        'is_review': False,
    })


@login_required
def review_queue(request):
    if request.method == 'POST':
        card = get_object_or_404(ReviewCard, id=request.POST.get('card_id'), user=request.user)
        question = get_object_or_404(Question, id=request.POST.get('question_id'))
        selected_ids = [cid for cid in request.POST.getlist('choice_id') if cid.isdigit()]
        result = record_quiz_answer(request.user, question, selected_ids)
        result['question'] = question
        result['selected_choices'] = list(question.choices.filter(id__in=selected_ids))
        result['correct_choices'] = list(question.choices.filter(is_correct=True))
        box_before = request.POST.get('box_before', '')
        card.refresh_from_db()
        return render(request, 'learn/review.html', {
            'result': result, 'card': None, 'next_question': None, 'choices': [],
            'box_before': int(box_before) if box_before.isdigit() else None,
            'box_after': _leitner_box(card),
            'due_left': due_review_cards(request.user).count(),
        })

    due = list(due_review_cards(request.user))
    if not due:
        upcoming = ReviewCard.objects.filter(user=request.user).order_by('due_at').first()
        return render(request, 'learn/review.html', {
            'result': None, 'card': None, 'next_question': None, 'choices': [], 'empty': True,
            'next_due': upcoming.due_at if upcoming else None,
        })
    card = random.choice(due)
    questions = list(card.concept.questions.all())
    question = random.choice(questions) if questions else None
    choices = list(question.choices.all()) if question else []
    random.shuffle(choices)
    return render(request, 'learn/review.html', {
        'result': None, 'card': card, 'next_question': question, 'choices': choices,
        'due_total': len(due), 'box': _leitner_box(card),
    })


@login_required
@require_POST
def toggle_unlock_all(request):
    """Superuser-only: flips a per-superuser flag that bypasses all chapter
    level-gating, so the whole book/chapter/concept tree is browsable
    regardless of level. Everyone else is bounced back untouched."""
    if not request.user.is_superuser:
        messages.error(request, "Only superusers can use that.")
        return redirect('learn:dashboard')

    profile = get_profile(request.user)
    profile.unlock_all_content = not profile.unlock_all_content
    profile.save(update_fields=['unlock_all_content'])
    messages.success(
        request,
        "All content unlocked for preview." if profile.unlock_all_content
        else "Content locking restored to normal level-gating.",
    )

    next_url = request.POST.get('next')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect('learn:dashboard')


@login_required
def badges_view(request):
    all_badges = list(Badge.objects.all())
    for badge in all_badges:
        # Stamp monogram: initials of the badge name ("Game Master" -> "GM").
        badge.initials = ''.join(w[0] for w in badge.name.split()[:2]).upper()
    earned_ids = set(UserBadge.objects.filter(user=request.user).values_list('badge_id', flat=True))
    return render(request, 'learn/badges.html', {
        'all_badges': all_badges, 'earned_ids': earned_ids,
    })


@login_required
def design_challenge(request, challenge_slug):
    challenge = get_object_or_404(DesignChallenge, slug=challenge_slug)
    profile = get_profile(request.user)
    if not chapter_is_unlocked(challenge.concept.chapter, profile):
        messages.error(request, "This chapter is still locked.")
        return redirect('learn:dashboard')

    result = None
    if request.method == 'POST':
        placed_raw = request.POST.get('placed_ids', '')
        conns_raw = request.POST.get('connections', '')
        placed_ids = {int(x) for x in placed_raw.split(',') if x.strip().isdigit()}
        connection_pairs = set()
        if conns_raw:
            for pair in conns_raw.split(';'):
                if '-' in pair:
                    a, b = pair.split('-', 1)
                    if a.strip().isdigit() and b.strip().isdigit():
                        connection_pairs.add(frozenset({int(a), int(b)}))
        result = record_design_attempt(request.user, challenge, placed_ids, connection_pairs)

    pool = list(challenge.pool_components.select_related('component_type'))
    random.shuffle(pool)
    return render(request, 'learn/design_challenge.html', {
        'challenge': challenge, 'pool': pool, 'result': result,
    })


@login_required
def matching_challenge(request, challenge_slug):
    challenge = get_object_or_404(MatchingChallenge, slug=challenge_slug)
    profile = get_profile(request.user)
    if not chapter_is_unlocked(challenge.concept.chapter, profile):
        messages.error(request, "This chapter is still locked.")
        return redirect('learn:dashboard')

    result = None
    if request.method == 'POST':
        try:
            submitted_map = json.loads(request.POST.get('answers', '{}'))
        except (ValueError, TypeError):
            submitted_map = {}
        submitted_map = {int(k): v for k, v in submitted_map.items() if str(v).strip()}
        result = record_matching_attempt(request.user, challenge, submitted_map)

    terms = list(challenge.pairs.all())
    definitions = list(challenge.pairs.all())
    random.shuffle(definitions)
    return render(request, 'learn/matching_challenge.html', {
        'challenge': challenge, 'terms': terms, 'definitions': definitions, 'result': result,
    })


@login_required
def ordering_challenge(request, challenge_slug):
    challenge = get_object_or_404(OrderingChallenge, slug=challenge_slug)
    profile = get_profile(request.user)
    if not chapter_is_unlocked(challenge.concept.chapter, profile):
        messages.error(request, "This chapter is still locked.")
        return redirect('learn:dashboard')

    result = None
    if request.method == 'POST':
        order_raw = request.POST.get('order', '')
        submitted_order = [int(x) for x in order_raw.split(',') if x.strip().isdigit()]
        result = record_ordering_attempt(request.user, challenge, submitted_order)

    steps = list(challenge.steps.all())
    random.shuffle(steps)
    return render(request, 'learn/ordering_challenge.html', {
        'challenge': challenge, 'steps': steps, 'result': result,
    })


@login_required
def coding_challenge(request, challenge_slug):
    challenge = get_object_or_404(CodingChallenge, slug=challenge_slug)
    profile = get_profile(request.user)
    if not chapter_is_unlocked(challenge.concept.chapter, profile):
        messages.error(request, "This chapter is still locked.")
        return redirect('learn:dashboard')

    result = None
    submitted_code = challenge.starter_code
    if request.method == 'POST':
        submitted_code = request.POST.get('code', '')
        result = record_coding_attempt(request.user, challenge, submitted_code)

    # Regular learners only ever see the first 2 sample-marked cases as
    # worked examples — everything else (extra samples included) stays
    # hidden. Superusers get every test case (stdin + expected output, not
    # just pass/fail) behind an explicit "view all" toggle in the template.
    visible_examples = list(challenge.sample_test_cases[:2])
    all_test_cases = list(challenge.test_cases.all()) if request.user.is_superuser else []

    return render(request, 'learn/coding_challenge.html', {
        'challenge': challenge,
        'sample_test_cases': visible_examples,
        'all_test_cases': all_test_cases,
        'result': result,
        'submitted_code': submitted_code,
    })


def _flaw_run_key(challenge):
    return f'flaw_run_{challenge.id}'


def _flaw_diagram(challenge):
    """Pre-computes where each part's text sits so the template can draw the
    SVG without arithmetic: box titles are centred (one or two lines), the
    state tag hangs off a box's top-right corner or under an arrow's caption."""
    nodes, edges = [], []
    for part in challenge.parts.all():
        g = part.geometry or {}
        if part.kind == FlawPart.EDGE:
            has_caption = bool(part.sublabel) and 'lx' in g and 'ly' in g
            edges.append({
                'key': part.key, 'label': part.label, 'd': g.get('d', ''),
                'caption': part.sublabel if has_caption else '',
                'lx': g.get('lx', 0), 'ly': g.get('ly', 0), 'tag_y': g.get('ly', 0) + 28,
            })
        else:
            x, y, w, h = (g.get(k, 0) for k in ('x', 'y', 'w', 'h'))
            mid = y + h / 2
            nodes.append({
                'key': part.key, 'label': part.label, 'sublabel': part.sublabel,
                'x': x, 'y': y, 'w': w, 'h': h, 'cx': x + w / 2,
                'title_y': mid - 3 if part.sublabel else mid + 5, 'sub_y': mid + 15,
                'tag_x': x + w, 'tag_y': y - 5,
            })
    return nodes, edges


@login_required
def flaw_challenge(request, challenge_slug):
    challenge = get_object_or_404(FlawChallenge.objects.select_related('concept__chapter__book'), slug=challenge_slug)
    profile = get_profile(request.user)
    if not chapter_is_unlocked(challenge.concept.chapter, profile):
        messages.error(request, "This chapter is still locked.")
        return redirect('learn:dashboard')

    # An unfinished review picks up where it left off, penalties included,
    # so reloading the page can't wipe a wrong tap. A closed one starts over.
    key = _flaw_run_key(challenge)
    run = request.session.get(key)
    if not run or run.get('done'):
        run = new_flaw_run()
        request.session[key] = run

    nodes, edges = _flaw_diagram(challenge)
    return render(request, 'learn/flaw_challenge.html', {
        'challenge': challenge, 'nodes': nodes, 'edges': edges,
        'snapshot': flaw_snapshot(challenge, run),
        'points': {
            'found': services.POINTS_FLAW_FOUND, 'wrong': services.POINTS_FLAW_WRONG_REASON,
            'healthy': services.POINTS_FLAW_HEALTHY_TAP, 'missed': services.POINTS_FLAW_MISSED,
            'perfect': services.PERFECT_BONUS,
        },
    })


@login_required
@require_POST
def flaw_move(request, challenge_slug):
    """One move in a Spot the Flaw review, answered as JSON: `inspect` a
    part, `answer` why a part is flawed, or `finish` the review. Finding the
    last flaw finishes it too."""
    challenge = get_object_or_404(FlawChallenge, slug=challenge_slug)
    profile = get_profile(request.user)
    if not chapter_is_unlocked(challenge.concept.chapter, profile):
        return JsonResponse({'error': 'This chapter is still locked.'}, status=403)

    key = _flaw_run_key(challenge)
    run = request.session.get(key)
    if not run or run.get('done'):
        return JsonResponse({'error': 'This review has already closed. Reload the page to start a new one.'}, status=409)

    action = request.POST.get('action')
    part_key = request.POST.get('part', '')
    if action == 'inspect':
        result = inspect_flaw_part(challenge, run, part_key)
    elif action == 'answer':
        reason = request.POST.get('reason', '')
        result = answer_flaw_part(challenge, run, part_key, int(reason)) if reason.isdigit() else None
    elif action == 'finish':
        result = {'verdict': 'finished', 'points': 0}
    else:
        result = None
    if result is None:
        return JsonResponse({'error': "That move doesn't fit this diagram."}, status=400)

    finished = None
    if action == 'finish' or all_flaws_found(challenge, run):
        finished = record_flaw_attempt(request.user, challenge, run)
        finished['new_badges'] = [b.name for b in finished['new_badges']]
    request.session[key] = run
    return JsonResponse({'result': result, 'finished': finished, 'snapshot': flaw_snapshot(challenge, run)})


@login_required
def traffic_challenge(request, challenge_slug):
    challenge = get_object_or_404(TrafficChallenge.objects.select_related('concept__chapter__book'), slug=challenge_slug)
    profile = get_profile(request.user)
    if not chapter_is_unlocked(challenge.concept.chapter, profile):
        messages.error(request, "This chapter is still locked.")
        return redirect('learn:dashboard')
    return render(request, 'learn/traffic_challenge.html', {
        'challenge': challenge, 'params': challenge.params,
        'error_pct': f"{challenge.params['slo']['error_rate'] * 100:g}",
        'perfect_bonus': services.PERFECT_BONUS, 'points_per_xp': services.TRAFFIC_POINTS_PER_XP,
    })


@login_required
@require_POST
def traffic_finish(request, challenge_slug):
    """Files a finished day. The body is {"plan": [[servers, replicas, cache,
    redirect], ...]}, one entry per tick; the server replays it to score."""
    challenge = get_object_or_404(TrafficChallenge, slug=challenge_slug)
    profile = get_profile(request.user)
    if not chapter_is_unlocked(challenge.concept.chapter, profile):
        return JsonResponse({'error': 'This chapter is still locked.'}, status=403)
    try:
        raw_plan = json.loads(request.body).get('plan')
    except (ValueError, AttributeError):
        raw_plan = None
    result = record_traffic_attempt(request.user, challenge, raw_plan)
    if result is None:
        return JsonResponse({'error': "That day's design plan didn't check out. Reset and run the day again."}, status=400)
    result['new_badges'] = [b.name for b in result['new_badges']]
    return JsonResponse(result)


def _quorum_run_key(challenge):
    return f'quorum_run_{challenge.id}'


@login_required
def quorum_challenge(request, challenge_slug):
    challenge = get_object_or_404(QuorumChallenge.objects.select_related('concept__chapter__book'), slug=challenge_slug)
    profile = get_profile(request.user)
    if not chapter_is_unlocked(challenge.concept.chapter, profile):
        messages.error(request, "This chapter is still locked.")
        return redirect('learn:dashboard')

    # An unfinished run picks up where it left off, bets and draws included,
    # so reloading can't redraw a read. A finished one starts over.
    key = _quorum_run_key(challenge)
    run = request.session.get(key)
    if not run or run.get('done') or not quorum.run_fits(challenge.tables, run):
        run = quorum.new_run()
        request.session[key] = run

    stakes = quorum.stakes()
    return render(request, 'learn/quorum_challenge.html', {
        'challenge': challenge, 'snapshot': quorum.snapshot(challenge.tables, run), 'stakes': stakes,
        'best': stakes[-1][0], 'worst': -stakes[-1][1], 'bet_range': (quorum.MIN_BET, quorum.MAX_BET),
        'calibrated_within': quorum.CALIBRATED_WITHIN, 'perfect_bonus': services.PERFECT_BONUS,
    })


@login_required
@require_POST
def quorum_move(request, challenge_slug):
    """One move in a Quorum Casino run, answered as JSON: `next` plays the
    next event (or opens the next table), and `bet` locks in `pct`, the
    learner's chance from 1 to 99 that the waiting read returns the last
    successful write. The run closes after the last table's last event."""
    challenge = get_object_or_404(QuorumChallenge, slug=challenge_slug)
    profile = get_profile(request.user)
    if not chapter_is_unlocked(challenge.concept.chapter, profile):
        return JsonResponse({'error': 'This chapter is still locked.'}, status=403)

    key = _quorum_run_key(challenge)
    run = request.session.get(key)
    if not run or run.get('done') or not quorum.run_fits(challenge.tables, run):
        return JsonResponse({'error': 'This run has already finished. Reload the page to play again.'}, status=409)

    action = request.POST.get('action')
    if action == 'next':
        result = quorum.advance(challenge.tables, run)
        error = 'Lock in your bet on this read first.'
    elif action == 'bet':
        pct = request.POST.get('pct', '')
        result = quorum.place_bet(challenge.tables, run, int(pct)) if pct.isdecimal() and len(pct) <= 3 else None
        error = f"That bet doesn't fit. Bets run from {quorum.MIN_BET}% to {quorum.MAX_BET}%, on a read that's waiting for one."
    else:
        result, error = None, "That move doesn't fit this game."
    if result is None:
        return JsonResponse({'error': error}, status=400)

    finished = None
    if run['done']:
        finished = record_quorum_attempt(request.user, challenge, run)
        finished['new_badges'] = [b.name for b in finished['new_badges']]
    request.session[key] = run
    return JsonResponse({'result': result, 'finished': finished, 'snapshot': quorum.snapshot(challenge.tables, run)})


def _ring_run_key(challenge):
    return f'ring_run_{challenge.id}'


@login_required
def ring_challenge(request, challenge_slug):
    challenge = get_object_or_404(RingChallenge.objects.select_related('concept__chapter__book'), slug=challenge_slug)
    profile = get_profile(request.user)
    if not chapter_is_unlocked(challenge.concept.chapter, profile):
        messages.error(request, "This chapter is still locked.")
        return redirect('learn:dashboard')

    # An unfinished run picks up where it left off, lock-ins and predictions
    # included, so reloading can't wipe a miss. A finished one starts over.
    key = _ring_run_key(challenge)
    run = request.session.get(key)
    if not run or run.get('done') or not ring.run_fits(challenge.stages, run):
        run = ring.new_run()
        request.session[key] = run

    return render(request, 'learn/ring_challenge.html', {
        'challenge': challenge, 'snapshot': ring.snapshot(challenge.stages, run),
        'ring_data': ring.ring_data(challenge.stages), 'keys': ring.KEYS, 'max_vnodes': ring.MAX_VNODES,
        'rules': {
            'balance': ring.BALANCE_POINTS, 'per_point': ring.POSITIONS_PER_POINT,
            'missed': ring.MISSED_LOCK, 'right': ring.PREDICT_RIGHT, 'wrong': ring.PREDICT_WRONG,
        },
        'perfect_bonus': services.PERFECT_BONUS, 'points_per_xp': services.RING_POINTS_PER_XP,
    })


@login_required
@require_POST
def ring_move(request, challenge_slug):
    """One move in a Ring Balancer run, answered as JSON: `lock` locks in `k`
    virtual nodes per server (`weighted` = 1 gives them in proportion to
    capacity), `answer` picks option `choice` for the waiting prediction, and
    `next` opens the next stage once this one is cleared. The run closes when
    the last stage clears."""
    challenge = get_object_or_404(RingChallenge, slug=challenge_slug)
    profile = get_profile(request.user)
    if not chapter_is_unlocked(challenge.concept.chapter, profile):
        return JsonResponse({'error': 'This chapter is still locked.'}, status=403)

    key = _ring_run_key(challenge)
    run = request.session.get(key)
    if not run or run.get('done') or not ring.run_fits(challenge.stages, run):
        return JsonResponse({'error': 'This run has already finished. Reload the page to play again.'}, status=409)

    def whole(name):
        raw = request.POST.get(name, '')
        return int(raw) if raw.isdecimal() and len(raw) <= 4 else None

    action = request.POST.get('action')
    if action == 'lock':
        weighted = request.POST.get('weighted', '0')
        result = ring.lock(challenge.stages, run, whole('k'), weighted == '1') if weighted in ('0', '1') else None
        error = f"That lock-in doesn't fit. Virtual nodes run from 1 to {ring.MAX_VNODES}, on a ring that's still to balance."
    elif action == 'answer':
        result = ring.answer(challenge.stages, run, whole('choice'))
        error = "That answer doesn't fit. Pick one of the options on a prediction that's waiting."
    elif action == 'next':
        result = ring.advance(challenge.stages, run)
        error = 'Clear this challenge first.'
    else:
        result, error = None, "That move doesn't fit this game."
    if result is None:
        return JsonResponse({'error': error}, status=400)

    finished = None
    if run['done']:
        finished = record_ring_attempt(request.user, challenge, run)
        finished['new_badges'] = [b.name for b in finished['new_badges']]
    request.session[key] = run
    return JsonResponse({'result': result, 'finished': finished, 'snapshot': ring.snapshot(challenge.stages, run)})
