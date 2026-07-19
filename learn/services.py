"""Gamification engine: XP, streaks, spaced repetition scheduling, mini-game scoring, badges."""
from django.db.models import Count
from django.utils import timezone

from .models import (
    Attempt, Badge, Book, Chapter, ConceptMastery,
    DesignAttempt, MatchingAttempt, OrderingAttempt,
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

PERFECT_BONUS = 25


def get_profile(user) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def record_quiz_answer(user, question, selected_choice, is_review=False):
    """Handles one quiz-question submission. Returns dict with result info."""
    is_correct = bool(selected_choice and selected_choice.is_correct)
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
    ('game_master', 'Game Master', 'Score a perfect run in the builder, matching, and ordering games.', '🎮'),
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
    maybe('architect', has_perfect_design)
    maybe('matchmaker', has_perfect_match)
    maybe('sequencer', has_perfect_order)
    maybe('game_master', has_perfect_design and has_perfect_match and has_perfect_order)

    return newly_earned


def chapter_is_unlocked(chapter, profile) -> bool:
    if profile.user.is_superuser and profile.unlock_all_content:
        return True
    return profile.level >= chapter.unlock_level


def due_review_cards(user):
    return ReviewCard.objects.filter(user=user, due_at__lte=timezone.now()).select_related('concept')
