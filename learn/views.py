import random

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Badge, Book, Chapter, Concept, ConceptMastery, DesignChallenge, MatchingChallenge,
    OrderingChallenge, Question, ReviewCard, UserBadge,
)
from .services import (
    chapter_is_unlocked, due_review_cards, get_profile, record_design_attempt,
    record_matching_attempt, record_ordering_attempt, record_quiz_answer,
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


@login_required
def dashboard(request):
    profile = get_profile(request.user)
    books = Book.objects.prefetch_related('chapters__concepts')
    book_data = []
    for book in books:
        chapters = []
        for chapter in book.chapters.all():
            total = chapter.concepts.count()
            mastered = ConceptMastery.objects.filter(
                user=request.user, concept__chapter=chapter,
                state=ConceptMastery.STATE_MASTERED,
            ).count()
            chapters.append({
                'chapter': chapter,
                'unlocked': chapter_is_unlocked(chapter, profile),
                'total': total,
                'mastered': mastered,
                'pct': int(100 * mastered / total) if total else 0,
            })
        book_data.append({'book': book, 'chapters': chapters})

    due_count = due_review_cards(request.user).count()
    earned_badges = UserBadge.objects.filter(user=request.user).select_related('badge')

    return render(request, 'learn/dashboard.html', {
        'profile': profile,
        'book_data': book_data,
        'due_count': due_count,
        'earned_badges': earned_badges,
        'xp_progress_pct': int(100 * profile.xp_into_level / profile.xp_for_next_level) if profile.xp_for_next_level else 100,
    })


@login_required
def book_detail(request, book_slug):
    book = get_object_or_404(Book, slug=book_slug)
    profile = get_profile(request.user)
    chapters = []
    for chapter in book.chapters.all():
        total = chapter.concepts.count()
        mastered = ConceptMastery.objects.filter(
            user=request.user, concept__chapter=chapter,
            state=ConceptMastery.STATE_MASTERED,
        ).count()
        chapters.append({
            'chapter': chapter,
            'unlocked': chapter_is_unlocked(chapter, profile),
            'total': total,
            'mastered': mastered,
        })
    return render(request, 'learn/book_detail.html', {'book': book, 'chapters': chapters})


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
        'design_challenges': concept.design_challenges.all(),
        'matching_challenges': concept.matching_challenges.all(),
        'ordering_challenges': concept.ordering_challenges.all(),
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
        choice_id = request.POST.get('choice_id')
        selected = question.choices.filter(id=choice_id).first() if choice_id else None
        result = record_quiz_answer(request.user, question, selected)
        result['question'] = question
        result['selected'] = selected
        result['correct_choice'] = question.choices.filter(is_correct=True).first()

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

    return render(request, 'learn/quiz.html', {
        'concept': concept,
        'result': result,
        'next_question': next_question,
        'choices': choices,
        'run': run,
        'empty': empty,
        'finished': finished,
        'is_review': False,
    })


@login_required
def review_queue(request):
    if request.method == 'POST':
        card = get_object_or_404(ReviewCard, id=request.POST.get('card_id'), user=request.user)
        question = get_object_or_404(Question, id=request.POST.get('question_id'))
        choice_id = request.POST.get('choice_id')
        selected = question.choices.filter(id=choice_id).first() if choice_id else None
        result = record_quiz_answer(request.user, question, selected)
        result['question'] = question
        result['selected'] = selected
        result['correct_choice'] = question.choices.filter(is_correct=True).first()
        return render(request, 'learn/review.html', {
            'result': result, 'card': None, 'next_question': None, 'choices': [],
        })

    due = list(due_review_cards(request.user))
    if not due:
        return render(request, 'learn/review.html', {
            'result': None, 'card': None, 'next_question': None, 'choices': [], 'empty': True,
        })
    card = random.choice(due)
    questions = list(card.concept.questions.all())
    question = random.choice(questions) if questions else None
    choices = list(question.choices.all()) if question else []
    random.shuffle(choices)
    return render(request, 'learn/review.html', {
        'result': None, 'card': card, 'next_question': question, 'choices': choices,
        'due_total': len(due),
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
    all_badges = Badge.objects.all()
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
