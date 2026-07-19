import datetime
import math

from django.conf import settings
from django.db import models
from django.utils import timezone


class Book(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class Chapter(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='chapters')
    slug = models.SlugField()
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    summary = models.TextField(blank=True)
    unlock_level = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['book__order', 'order', 'id']
        unique_together = [('book', 'slug')]

    def __str__(self):
        return f'{self.book.title} - {self.title}'


class Concept(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='concepts')
    slug = models.SlugField()
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    summary = models.TextField(help_text='Short one- or two-sentence teaser shown above the Notes toggle.')
    source_note = models.CharField(max_length=255, blank=True)
    notes_sections = models.JSONField(
        default=list, blank=True,
        help_text=(
            "Structured notes, rendered behind the 'View Notes' toggle. "
            "List of {heading, body, deep_dive: {title, body} | null}. "
            "Also powers Study Mode (one flashcard per section)."
        ),
    )

    class Meta:
        ordering = ['chapter__book__order', 'chapter__order', 'order', 'id']
        unique_together = [('chapter', 'slug')]

    def __str__(self):
        return self.title


class Question(models.Model):
    MCQ = 'mcq'
    TRUE_FALSE = 'tf'
    KIND_CHOICES = [(MCQ, 'Multiple choice'), (TRUE_FALSE, 'True / False')]

    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name='questions')
    kind = models.CharField(max_length=8, choices=KIND_CHOICES, default=MCQ)
    prompt = models.TextField()
    explanation = models.TextField(blank=True)
    difficulty = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return self.prompt[:60]


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.text


def level_for_xp(xp: int) -> int:
    level = 1
    while xp_for_level(level + 1) <= xp:
        level += 1
    return level


def xp_for_level(level: int) -> int:
    if level <= 1:
        return 0
    return int(50 * (level - 1) * level / 2)


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    xp = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    unlock_all_content = models.BooleanField(
        default=False,
        help_text='Superuser-only preview toggle: bypasses chapter level-gating entirely.',
    )

    @property
    def level(self) -> int:
        return level_for_xp(self.xp)

    @property
    def xp_into_level(self) -> int:
        return self.xp - xp_for_level(self.level)

    @property
    def xp_for_next_level(self) -> int:
        return xp_for_level(self.level + 1) - xp_for_level(self.level)

    def add_xp(self, amount: int):
        self.xp = max(0, self.xp + amount)
        self.save(update_fields=['xp'])

    def touch_streak(self):
        today = timezone.localdate()
        if self.last_activity_date == today:
            return
        if self.last_activity_date == today - datetime.timedelta(days=1):
            self.current_streak += 1
        else:
            self.current_streak = 1
        self.longest_streak = max(self.longest_streak, self.current_streak)
        self.last_activity_date = today
        self.save(update_fields=['current_streak', 'longest_streak', 'last_activity_date'])

    def __str__(self):
        return f'{self.user.username} (Lv.{self.level}, {self.xp} XP)'


class Attempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attempts')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='attempts')
    is_correct = models.BooleanField()
    xp_awarded = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class ReviewCard(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='review_cards')
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name='review_cards')
    ease_factor = models.FloatField(default=2.5)
    interval_days = models.FloatField(default=0)
    repetitions = models.PositiveIntegerField(default=0)
    due_at = models.DateTimeField(default=timezone.now)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [('user', 'concept')]

    def schedule(self, quality: int):
        quality = max(0, min(5, quality))
        if quality < 3:
            self.repetitions = 0
            self.interval_days = 1
        else:
            if self.repetitions == 0:
                self.interval_days = 1
            elif self.repetitions == 1:
                self.interval_days = 6
            else:
                self.interval_days = round(self.interval_days * self.ease_factor, 2)
            self.repetitions += 1

        self.ease_factor = max(
            1.3,
            self.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
        )
        self.last_reviewed_at = timezone.now()
        self.due_at = timezone.now() + datetime.timedelta(days=self.interval_days)
        self.save()

    @property
    def is_due(self) -> bool:
        return self.due_at <= timezone.now()

    def __str__(self):
        return f'{self.user.username} / {self.concept.title}'


class Badge(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    icon = models.CharField(max_length=10, default='star')

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='holders')
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'badge')]
        ordering = ['-earned_at']


class ConceptMastery(models.Model):
    STATE_LOCKED = 'locked'
    STATE_AVAILABLE = 'available'
    STATE_LEARNING = 'learning'
    STATE_MASTERED = 'mastered'
    STATE_CHOICES = [
        (STATE_LOCKED, 'Locked'),
        (STATE_AVAILABLE, 'Available'),
        (STATE_LEARNING, 'Learning'),
        (STATE_MASTERED, 'Mastered'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mastery')
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name='mastery')
    state = models.CharField(max_length=12, choices=STATE_CHOICES, default=STATE_AVAILABLE)
    correct_count = models.PositiveIntegerField(default=0)
    incorrect_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [('user', 'concept')]

    def __str__(self):
        return f'{self.user.username} / {self.concept.title}: {self.state}'


# ---------------------------------------------------------------------------
# Mini-games: architecture builder, matching, ordering
# ---------------------------------------------------------------------------

class ComponentType(models.Model):
    """A reusable system-design building block, e.g. 'Load Balancer', 'Cache'."""
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, default='\U0001F9E9')  # puzzle piece
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class DesignChallenge(models.Model):
    """Drag components from a pool onto a canvas and wire them up correctly."""
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name='design_challenges')
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    prompt = models.TextField(help_text='The scenario shown to the player, e.g. "Design a URL shortener".')
    difficulty = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return self.title

    @property
    def required_components(self):
        return self.pool_components.filter(is_required=True)

    @property
    def distractor_components(self):
        return self.pool_components.filter(is_distractor=True)


class DesignChallengeComponent(models.Model):
    """One entry in a challenge's component pool."""
    challenge = models.ForeignKey(DesignChallenge, on_delete=models.CASCADE, related_name='pool_components')
    component_type = models.ForeignKey(ComponentType, on_delete=models.CASCADE)
    is_required = models.BooleanField(default=False, help_text='Correct to place on the canvas.')
    is_distractor = models.BooleanField(default=False, help_text='Wrong for this scenario — placing it costs points.')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        unique_together = [('challenge', 'component_type')]

    def __str__(self):
        return f'{self.challenge.title}: {self.component_type.name}'


class DesignChallengeConnection(models.Model):
    """A correct wire between two component types for a given challenge."""
    challenge = models.ForeignKey(DesignChallenge, on_delete=models.CASCADE, related_name='correct_connections')
    from_component = models.ForeignKey(ComponentType, on_delete=models.CASCADE, related_name='+')
    to_component = models.ForeignKey(ComponentType, on_delete=models.CASCADE, related_name='+')

    class Meta:
        unique_together = [('challenge', 'from_component', 'to_component')]

    def __str__(self):
        return f'{self.from_component.name} -> {self.to_component.name}'


class DesignAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='design_attempts')
    challenge = models.ForeignKey(DesignChallenge, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField(default=0)
    xp_awarded = models.IntegerField(default=0)
    is_perfect = models.BooleanField(default=False)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class MatchingChallenge(models.Model):
    """Drag each definition onto the term it defines."""
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name='matching_challenges')
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    instructions = models.CharField(max_length=255, default='Drag each definition onto the term it matches.')

    def __str__(self):
        return self.title


class MatchingPair(models.Model):
    challenge = models.ForeignKey(MatchingChallenge, on_delete=models.CASCADE, related_name='pairs')
    term = models.CharField(max_length=150)
    definition = models.CharField(max_length=500)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.term


class MatchingAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='matching_attempts')
    challenge = models.ForeignKey(MatchingChallenge, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField(default=0)
    xp_awarded = models.IntegerField(default=0)
    is_perfect = models.BooleanField(default=False)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class OrderingChallenge(models.Model):
    """Drag steps into the correct sequence."""
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name='ordering_challenges')
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    instructions = models.CharField(max_length=255, default='Drag the steps into the correct order.')

    def __str__(self):
        return self.title


class OrderingStep(models.Model):
    challenge = models.ForeignKey(OrderingChallenge, on_delete=models.CASCADE, related_name='steps')
    text = models.CharField(max_length=300)
    correct_position = models.PositiveIntegerField()

    class Meta:
        ordering = ['correct_position', 'id']

    def __str__(self):
        return f'{self.correct_position}: {self.text[:40]}'


class OrderingAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ordering_attempts')
    challenge = models.ForeignKey(OrderingChallenge, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField(default=0)
    xp_awarded = models.IntegerField(default=0)
    is_perfect = models.BooleanField(default=False)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
