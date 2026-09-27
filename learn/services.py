"""Gamification engine: XP, streaks, spaced repetition scheduling, mini-game scoring, badges."""
import random

from django.db.models import Count
from django.utils import timezone

from .code_runner import grade_submission
from .models import (
    Attempt, Badge, Book, Chapter, ConceptMastery,
    CodingAttempt, DesignAttempt, FlawAttempt, MatchingAttempt, OrderingAttempt,
    ReviewCard, UserBadge, UserProfile,
)

XP_CORRECT_BASE = 10
XP_WRONG_PARTICIPATION = 2

# Architecture-builder scoring
POINTS_REQUIRED = 15
POINTS_DISTRACTOR_PENALTY = 10
POINTS_MISSING_PENALTY = 5
POINTS_CONN_CORRECT = 10
POINTS_CONN_WRONG = 8
POINTS_CONN_MISSING = 4

# Matching-game scoring
POINTS_MATCH_CORRECT = 10
POINTS_MATCH_WRONG = 5

# Ordering-game scoring
POINTS_ORDER_CORRECT = 8
POINTS_ORDER_WRONG = 4

# Coding-challenge scoring
POINTS_TEST_PASSED = 12
POINTS_TEST_FAILED = 3

# Spot-the-flaw scoring
POINTS_FLAW_FOUND = 25
POINTS_FLAW_WRONG_REASON = 10
POINTS_FLAW_HEALTHY_TAP = 10
POINTS_FLAW_MISSED = 15

PERFECT_BONUS = 25


def get_profile(user) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def record_quiz_answer(user, question, selected_choice_ids, is_review=False):
    """Handles one quiz-question submission. `selected_choice_ids` is an
    iterable of Choice ids the learner picked (a single-element iterable for
    MCQ/True-False; any number for a "select all that apply" multi-select
    question). Grading is an exact-set match against every choice marked
    `is_correct=True` on the question — every correct option must be picked
    and no incorrect one — so the "one confirmed correct answer" guarantee
    holds for single-answer questions and the analogous "every correct box
    checked, no wrong one" guarantee holds for multi-select. Returns dict
    with result info."""
    selected_ids = {int(cid) for cid in selected_choice_ids if cid is not None}
    correct_ids = set(question.choices.filter(is_correct=True).values_list('id', flat=True))
    is_correct = bool(selected_ids) and selected_ids == correct_ids
    xp = XP_CORRECT_BASE * question.difficulty if is_correct else XP_WRONG_PARTICIPATION

    Attempt.objects.create(user=user, question=question, is_correct=is_correct, xp_awarded=xp)

    profile = get_profile(user)
    old_level = profile.level
    profile.add_xp(xp)
    profile.touch_streak()
    new_level = profile.level

    concept = question.concept
    mastery, _ = ConceptMastery.objects.get_or_create(
        user=user, concept=concept, defaults={'state': ConceptMastery.STATE_LEARNING},
    )
    if is_correct:
        mastery.correct_count += 1
    else:
        mastery.incorrect_count += 1
    if mastery.state == ConceptMastery.STATE_AVAILABLE:
        mastery.state = ConceptMastery.STATE_LEARNING
    total = mastery.correct_count + mastery.incorrect_count
    if mastery.correct_count >= 3 and total > 0 and mastery.correct_count / total >= 0.7:
        mastery.state = ConceptMastery.STATE_MASTERED
    mastery.save()

    card, _ = ReviewCard.objects.get_or_create(user=user, concept=concept)
    card.schedule(5 if is_correct else 1)

    newly_earned = check_badges(user)

    return {
        'is_correct': is_correct, 'xp_awarded': xp,
        'leveled_up': new_level > old_level, 'new_level': new_level,
        'mastery_state': mastery.state, 'new_badges': newly_earned,
    }


def record_design_attempt(user, challenge, placed_ids, connection_pairs):
    """placed_ids: set[int] of ComponentType ids dropped on the canvas.
    connection_pairs: set[frozenset({int,int})] of component-type id pairs the player wired together."""
    pool = list(challenge.pool_components.select_related('component_type'))
    required_ids = {p.component_type_id for p in pool if p.is_required}
    distractor_ids = {p.component_type_id for p in pool if p.is_distractor}
    name_by_id = {p.component_type_id: p.component_type.name for p in pool}

    score = 0
    used_required, used_distractors, missing_required = [], [], []

    for cid in placed_ids:
        if cid in required_ids:
            score += POINTS_REQUIRED
            used_required.append(name_by_id.get(cid, cid))
        elif cid in distractor_ids:
            score -= POINTS_DISTRACTOR_PENALTY
            used_distractors.append(name_by_id.get(cid, cid))
        # anything else placed is neutral (0 points) — allows optional/no-penalty components

    for cid in required_ids - set(placed_ids):
        score -= POINTS_MISSING_PENALTY
        missing_required.append(name_by_id.get(cid, cid))

    correct_conns = {
        frozenset({c.from_component_id, c.to_component_id})
        for c in challenge.correct_connections.all()
    }
    submitted = set(connection_pairs)
    correct_used = submitted & correct_conns
    wrong_used = submitted - correct_conns
    missing_conns = correct_conns - submitted

    score += len(correct_used) * POINTS_CONN_CORRECT
    score -= len(wrong_used) * POINTS_CONN_WRONG
    score -= len(missing_conns) * POINTS_CONN_MISSING

    is_perfect = bool(
        not missing_required and not used_distractors
        and not wrong_used and not missing_conns and required_ids
    )
    if is_perfect:
        score += PERFECT_BONUS

    xp_awarded = max(0, score)
    profile = get_profile(user)
    old_level = profile.level
    profile.add_xp(xp_awarded)
    profile.touch_streak()
    new_level = profile.level

    detail = {
        'used_required': used_required, 'used_distractors': used_distractors,
        'missing_required': missing_required,
        'correct_connections': len(correct_used), 'wrong_connections': len(wrong_used),
        'missing_connections': len(missing_conns),
    }
    DesignAttempt.objects.create(
        user=user, challenge=challenge, score=score, xp_awarded=xp_awarded,
        is_perfect=is_perfect, detail=detail,
    )

    return {
        'score': score, 'xp_awarded': xp_awarded, 'is_perfect': is_perfect,
        'leveled_up': new_level > old_level, 'new_level': new_level,
        'detail': detail, 'new_badges': check_badges(user),
    }


def record_matching_attempt(user, challenge, submitted_map):
    """submitted_map: dict[term_pair_id (int) -> definition_pair_id the player dropped there]."""
    score = 0
    correct_terms, wrong_terms = [], []
    for pair in challenge.pairs.all():
        chosen = submitted_map.get(pair.id) or submitted_map.get(str(pair.id))
        if chosen is not None and int(chosen) == pair.id:
            score += POINTS_MATCH_CORRECT
            correct_terms.append(pair.term)
        else:
            score -= POINTS_MATCH_WRONG
            wrong_terms.append(pair.term)

    is_perfect = bool(not wrong_terms and challenge.pairs.exists())
    if is_perfect:
        score += PERFECT_BONUS

    xp_awarded = max(0, score)
    profile = get_profile(user)
    old_level = profile.level
    profile.add_xp(xp_awarded)
    profile.touch_streak()
    new_level = profile.level

    detail = {'correct_terms': correct_terms, 'wrong_terms': wrong_terms}
    MatchingAttempt.objects.create(
        user=user, challenge=challenge, score=score, xp_awarded=xp_awarded,
        is_perfect=is_perfect, detail=detail,
    )
    return {
        'score': score, 'xp_awarded': xp_awarded, 'is_perfect': is_perfect,
        'leveled_up': new_level > old_level, 'new_level': new_level,
        'detail': detail, 'new_badges': check_badges(user),
    }


def record_ordering_attempt(user, challenge, submitted_order_ids):
    """submitted_order_ids: list[int] of OrderingStep ids in the order the player placed them."""
    steps = {s.id: s for s in challenge.steps.all()}
    score = 0
    correct_count = 0
    wrong_count = 0
    for i, step_id in enumerate(submitted_order_ids, start=1):
        step = steps.get(int(step_id))
        if step and step.correct_position == i:
            score += POINTS_ORDER_CORRECT
            correct_count += 1
        else:
            score -= POINTS_ORDER_WRONG
            wrong_count += 1

    is_perfect = bool(wrong_count == 0 and len(submitted_order_ids) == len(steps) and steps)
    if is_perfect:
        score += PERFECT_BONUS

    xp_awarded = max(0, score)
    profile = get_profile(user)
    old_level = profile.level
    profile.add_xp(xp_awarded)
    profile.touch_streak()
    new_level = profile.level

    detail = {'correct_count': correct_count, 'wrong_count': wrong_count, 'total': len(steps)}
    OrderingAttempt.objects.create(
        user=user, challenge=challenge, score=score, xp_awarded=xp_awarded,
        is_perfect=is_perfect, detail=detail,
    )
    return {
        'score': score, 'xp_awarded': xp_awarded, 'is_perfect': is_perfect,
        'leveled_up': new_level > old_level, 'new_level': new_level,
        'detail': detail, 'new_badges': check_badges(user),
    }


def record_coding_attempt(user, challenge, code):
    """Grades `code` against every one of the challenge's test cases (via
    learn.code_runner, in a subprocess sandbox — see that module's docstring
    for what is and isn't isolated), then scores it with the same
    never-free-to-guess-wrong principle as the other mini-games: passing
    tests score, failing ones cost a little, and a fully-passing run earns
    the perfect bonus."""
    grading = grade_submission(code, challenge.test_cases.all())
    passed, total = grading['passed_count'], grading['total_count']

    score = passed * POINTS_TEST_PASSED - (total - passed) * POINTS_TEST_FAILED
    is_perfect = bool(total > 0 and passed == total)
    if is_perfect:
        score += PERFECT_BONUS

    xp_awarded = max(0, score)
    profile = get_profile(user)
    old_level = profile.level
    profile.add_xp(xp_awarded)
    profile.touch_streak()
    new_level = profile.level

    # Hidden test cases stay hidden even in the result detail — only
    # pass/fail, not stdin/expected/stdout — sample cases show the full diff
    # so the learner has something to debug against.
    visible_results = []
    for r in grading['results']:
        if r['is_sample']:
            visible_results.append(r)
        else:
            visible_results.append({
                'test_case_id': r['test_case_id'], 'is_sample': False, 'passed': r['passed'],
                'timed_out': r['timed_out'], 'blocked_reason': r['blocked_reason'],
            })

    detail = {'passed': passed, 'total': total, 'results': visible_results}
    CodingAttempt.objects.create(
        user=user, challenge=challenge, code=code, score=score, xp_awarded=xp_awarded,
        is_perfect=is_perfect, detail=detail,
    )
    return {
        'score': score, 'xp_awarded': xp_awarded, 'is_perfect': is_perfect,
        'leveled_up': new_level > old_level, 'new_level': new_level,
        'detail': detail, 'new_badges': check_badges(user),
    }


# ---------------------------------------------------------------------------
# Spot the Flaw
#
# Unlike the other games, this one gives feedback on every tap, so a run is
# a small state machine that the view keeps in the session instead of one
# form submit at the end. The run only records what the learner has done
# (flaws found, healthy parts tapped, wrong reasons tried) and the score is
# recomputed from that. Whether a part is flawed, and which reason is right,
# never reaches the page until the learner has committed to an answer.
# ---------------------------------------------------------------------------

def new_flaw_run():
    return {'seed': random.randrange(1 << 30), 'found': [], 'cleared': [], 'wrong': {}, 'done': False}


def _flaw_parts(challenge):
    return {p.key: p for p in challenge.parts.prefetch_related('reasons')}


def _flaw_note(part):
    """What a part says once it's resolved: the fix for a flaw, or why a healthy part is fine."""
    if part.is_flaw:
        right = next((r for r in part.reasons.all() if r.is_correct), None)
        return right.text if right else part.explanation
    return part.explanation


def _missed_keys(parts, run):
    if not run['done']:
        return []
    return [k for k, p in parts.items() if p.is_flaw and k not in run['found']]


def _flaw_is_perfect(parts, run):
    flaw_keys = {k for k, p in parts.items() if p.is_flaw}
    return bool(flaw_keys and set(run['found']) == flaw_keys
                and not run['cleared'] and not any(run['wrong'].values()))


def _flaw_score(parts, run):
    score = (
        len(run['found']) * POINTS_FLAW_FOUND
        - len(run['cleared']) * POINTS_FLAW_HEALTHY_TAP
        - sum(len(ids) for ids in run['wrong'].values()) * POINTS_FLAW_WRONG_REASON
        - len(_missed_keys(parts, run)) * POINTS_FLAW_MISSED
    )
    if run['done'] and _flaw_is_perfect(parts, run):
        score += PERFECT_BONUS
    return score


def flaw_snapshot(challenge, run):
    """The public view of a run: the score so far and, for each part the
    learner has resolved (or every part, once the review is closed), its
    state and note. Unresolved parts are left out entirely."""
    parts = _flaw_parts(challenge)
    missed = set(_missed_keys(parts, run))
    public = {}
    for key, part in parts.items():
        if key in run['found']:
            state = 'found'
        elif key in run['cleared']:
            state = 'fine'
        elif key in missed:
            state = 'missed'
        elif run['done']:
            state = 'unchecked'
        else:
            continue
        public[key] = {'state': state, 'note': _flaw_note(part)}
    return {
        'score': _flaw_score(parts, run),
        'found': len(run['found']),
        'flaws': sum(1 for p in parts.values() if p.is_flaw),
        'done': run['done'],
        'parts': public,
    }


def _reason_options(part, run):
    reasons = list(part.reasons.all())
    random.Random(f"{run['seed']}:{part.key}").shuffle(reasons)
    tried = set(run['wrong'].get(part.key, []))
    return [{'id': r.id, 'text': r.text, 'tried': r.id in tried} for r in reasons]


def inspect_flaw_part(challenge, run, key):
    """The learner tapped a part. A healthy part costs points on its first
    tap and is marked fine; a flawed part asks them why it's wrong.
    Returns None for a key that isn't in the diagram."""
    part = _flaw_parts(challenge).get(key)
    if part is None:
        return None
    if run['done'] or key in run['found'] or key in run['cleared']:
        return {'verdict': 'resolved', 'points': 0}
    if not part.is_flaw:
        run['cleared'].append(key)
        return {'verdict': 'fine', 'points': -POINTS_FLAW_HEALTHY_TAP}
    return {'verdict': 'suspect', 'points': 0, 'reasons': _reason_options(part, run)}


def answer_flaw_part(challenge, run, key, reason_id):
    """The learner said why a flawed part is wrong. A wrong reason costs
    points once and is crossed off; the right one marks the flaw found.
    Returns None unless the reason belongs to a flawed part with that key."""
    part = _flaw_parts(challenge).get(key)
    if part is None or not part.is_flaw:
        return None
    reason = next((r for r in part.reasons.all() if r.id == reason_id), None)
    if reason is None:
        return None
    if run['done'] or key in run['found']:
        return {'verdict': 'resolved', 'points': 0}
    if reason.is_correct:
        run['found'].append(key)
        return {'verdict': 'right', 'points': POINTS_FLAW_FOUND}
    tried = run['wrong'].setdefault(key, [])
    points = 0
    if reason.id not in tried:
        tried.append(reason.id)
        points = -POINTS_FLAW_WRONG_REASON
    return {'verdict': 'wrong', 'points': points, 'reasons': _reason_options(part, run)}


def all_flaws_found(challenge, run):
    return all(k in run['found'] for k, p in _flaw_parts(challenge).items() if p.is_flaw)


def record_flaw_attempt(user, challenge, run):
    """Closes the review: every flaw still hidden costs points, a clean run
    earns the perfect bonus, and the attempt is filed like every other game."""
    run['done'] = True
    parts = _flaw_parts(challenge)
    missed = _missed_keys(parts, run)
    is_perfect = _flaw_is_perfect(parts, run)
    score = _flaw_score(parts, run)

    xp_awarded = max(0, score)
    profile = get_profile(user)
    old_level = profile.level
    profile.add_xp(xp_awarded)
    profile.touch_streak()
    new_level = profile.level

    detail = {
        'found': [parts[k].label for k in run['found'] if k in parts],
        'missed': [parts[k].label for k in missed],
        'healthy_taps': [parts[k].label for k in run['cleared'] if k in parts],
        'wrong_reasons': sum(len(ids) for ids in run['wrong'].values()),
    }
    FlawAttempt.objects.create(
        user=user, challenge=challenge, score=score, xp_awarded=xp_awarded,
        is_perfect=is_perfect, detail=detail,
    )
    return {
        'score': score, 'xp_awarded': xp_awarded, 'is_perfect': is_perfect,
        'leveled_up': new_level > old_level, 'new_level': new_level,
        'detail': detail, 'new_badges': check_badges(user),
    }


BADGE_DEFS = [
    ('first_blood', 'First Blood', 'Answer your first question correctly.', '🎯'),
    ('streak_3', 'Warming Up', 'Reach a 3-day learning streak.', '🔥'),
    ('streak_7', 'On Fire', 'Reach a 7-day learning streak.', '🔥'),
    ('streak_30', 'Unstoppable', 'Reach a 30-day learning streak.', '🚀'),
    ('level_5', 'Rising Engineer', 'Reach level 5.', '⭐'),
    ('level_10', 'Staff Material', 'Reach level 10.', '🌟'),
    ('chapter_champion', 'Chapter Champion', 'Master every concept in a chapter.', '🏆'),
    ('book_worm', 'Book Worm', 'Master every concept in an entire book.', '📚'),
    ('reviewer', 'Spaced Out', 'Complete 10 spaced-repetition reviews.', '🧠'),
    ('architect', 'Architect', 'Build a perfect system design — no wrong parts, no wrong wires.', '🏗️'),
    ('matchmaker', 'Matchmaker', 'Get every match correct in a matching challenge.', '🧩'),
    ('sequencer', 'Sequencer', 'Put every step in exactly the right order.', '🔢'),
    ('coder', 'Coder', 'Pass every test case on a coding challenge.', '💻'),
    ('flaw_finder', 'Flaw Finder', 'Find every planted flaw without a wrong tap or a wrong reason.', '🔍'),
    ('game_master', 'Game Master', 'Score a perfect run in the builder, matching, ordering, and coding games.', '🎮'),
]


def ensure_badges_exist():
    for slug, name, desc, icon in BADGE_DEFS:
        Badge.objects.get_or_create(slug=slug, defaults={'name': name, 'description': desc, 'icon': icon})


def award_badge(user, slug):
    try:
        badge = Badge.objects.get(slug=slug)
    except Badge.DoesNotExist:
        return None
    ub, created = UserBadge.objects.get_or_create(user=user, badge=badge)
    return badge if created else None


def check_badges(user):
    ensure_badges_exist()
    newly_earned = []
    profile = get_profile(user)

    def maybe(slug, condition):
        if condition:
            b = award_badge(user, slug)
            if b:
                newly_earned.append(b)

    maybe('first_blood', Attempt.objects.filter(user=user, is_correct=True).exists())
    maybe('streak_3', profile.current_streak >= 3)
    maybe('streak_7', profile.current_streak >= 7)
    maybe('streak_30', profile.current_streak >= 30)
    maybe('level_5', profile.level >= 5)
    maybe('level_10', profile.level >= 10)

    for chapter in Chapter.objects.all():
        total = chapter.concepts.count()
        if total == 0:
            continue
        mastered = ConceptMastery.objects.filter(
            user=user, concept__chapter=chapter, state=ConceptMastery.STATE_MASTERED,
        ).count()
        maybe('chapter_champion', mastered >= total)

    for book in Book.objects.all():
        total = book.chapters.aggregate(n=Count('concepts'))['n'] or 0
        if total == 0:
            continue
        mastered = ConceptMastery.objects.filter(
            user=user, concept__chapter__book=book, state=ConceptMastery.STATE_MASTERED,
        ).count()
        maybe('book_worm', mastered >= total)

    review_count = ReviewCard.objects.filter(user=user, last_reviewed_at__isnull=False).count()
    maybe('reviewer', review_count >= 10)

    has_perfect_design = DesignAttempt.objects.filter(user=user, is_perfect=True).exists()
    has_perfect_match = MatchingAttempt.objects.filter(user=user, is_perfect=True).exists()
    has_perfect_order = OrderingAttempt.objects.filter(user=user, is_perfect=True).exists()
    has_perfect_coding = CodingAttempt.objects.filter(user=user, is_perfect=True).exists()
    maybe('flaw_finder', FlawAttempt.objects.filter(user=user, is_perfect=True).exists())
    maybe('architect', has_perfect_design)
    maybe('matchmaker', has_perfect_match)
    maybe('sequencer', has_perfect_order)
    maybe('coder', has_perfect_coding)
    maybe('game_master', has_perfect_design and has_perfect_match and has_perfect_order and has_perfect_coding)

    return newly_earned


def chapter_is_unlocked(chapter, profile) -> bool:
    if profile.user.is_superuser and profile.unlock_all_content:
        return True
    return profile.level >= chapter.unlock_level


def due_review_cards(user):
    return ReviewCard.objects.filter(user=user, due_at__lte=timezone.now()).select_related('concept')
