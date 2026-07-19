from django.contrib import admin

from .models import (
    Attempt, Badge, Book, Chapter, Choice, ComponentType, Concept, ConceptMastery,
    DesignAttempt, DesignChallenge, DesignChallengeComponent, DesignChallengeConnection,
    MatchingAttempt, MatchingChallenge, MatchingPair,
    OrderingAttempt, OrderingChallenge, OrderingStep,
    Question, ReviewCard, UserBadge, UserProfile,
)


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('prompt_short', 'concept', 'kind', 'difficulty')
    list_filter = ('concept__chapter__book', 'kind', 'difficulty')
    inlines = [ChoiceInline]

    def prompt_short(self, obj):
        return obj.prompt[:70]


class ConceptInline(admin.TabularInline):
    model = Concept
    extra = 0


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('title', 'book', 'order', 'unlock_level')
    list_filter = ('book',)
    inlines = [ConceptInline]


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'order')


class DesignChallengeComponentInline(admin.TabularInline):
    model = DesignChallengeComponent
    extra = 3


class DesignChallengeConnectionInline(admin.TabularInline):
    model = DesignChallengeConnection
    fk_name = 'challenge'
    extra = 2


@admin.register(DesignChallenge)
class DesignChallengeAdmin(admin.ModelAdmin):
    list_display = ('title', 'concept', 'difficulty')
    inlines = [DesignChallengeComponentInline, DesignChallengeConnectionInline]


@admin.register(ComponentType)
class ComponentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'slug')


class MatchingPairInline(admin.TabularInline):
    model = MatchingPair
    extra = 2


@admin.register(MatchingChallenge)
class MatchingChallengeAdmin(admin.ModelAdmin):
    list_display = ('title', 'concept')
    inlines = [MatchingPairInline]


class OrderingStepInline(admin.TabularInline):
    model = OrderingStep
    extra = 2


@admin.register(OrderingChallenge)
class OrderingChallengeAdmin(admin.ModelAdmin):
    list_display = ('title', 'concept')
    inlines = [OrderingStepInline]


admin.site.register(Concept)
admin.site.register(UserProfile)
admin.site.register(Attempt)
admin.site.register(ReviewCard)
admin.site.register(Badge)
admin.site.register(UserBadge)
admin.site.register(ConceptMastery)
admin.site.register(DesignAttempt)
admin.site.register(MatchingAttempt)
admin.site.register(OrderingAttempt)
