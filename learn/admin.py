import json

from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.text import slugify

from . import llm
from .models import (
    Attempt, Badge, Book, Chapter, Choice, CodingAttempt, CodingChallenge, ComponentType,
    Concept, ConceptMastery,
    DesignAttempt, DesignChallenge, DesignChallengeComponent, DesignChallengeConnection,
    FlawAttempt, FlawChallenge, FlawPart, FlawReason,
    MatchingAttempt, MatchingChallenge, MatchingPair,
    OrderingAttempt, OrderingChallenge, OrderingStep,
    Question, ReviewCard, TestCase, Topic, TrafficAttempt, TrafficChallenge, UserBadge, UserProfile,
)


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('prompt_short', 'concept', 'kind', 'difficulty')
    list_filter = ('concept__chapter__topic', 'concept__chapter__book', 'kind', 'difficulty')
    inlines = [ChoiceInline]

    def prompt_short(self, obj):
        return obj.prompt[:70]


class ConceptInline(admin.TabularInline):
    model = Concept
    extra = 0


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic', 'difficulty', 'book', 'order', 'unlock_level')
    list_filter = ('topic', 'difficulty', 'book')
    inlines = [ConceptInline]


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'order')


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


class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 2


DIFFICULTY_CHOICES = [(str(i), str(i)) for i in range(1, 6)]


@admin.register(CodingChallenge)
class CodingChallengeAdmin(admin.ModelAdmin):
    """Coding challenges are normally created via the "Generate from scenario"
    button (see change_list_template below / generate_view), which calls
    Gemini (learn/llm.py) to turn an admin-written scenario into a title,
    prompt, starter code, and test cases — asking clarifying questions
    instead of guessing if the scenario is missing what it needs. Test
    cases can still be hand-edited afterward via the inline below, same as
    every other content type in this app."""
    list_display = ('title', 'concept', 'difficulty', 'test_case_count')
    list_filter = ('concept__chapter__topic', 'concept__chapter__book', 'difficulty')
    inlines = [TestCaseInline]
    change_list_template = 'admin/learn/codingchallenge/change_list.html'
    fields = ('concept', 'slug', 'title', 'prompt', 'constraints', 'starter_code', 'difficulty', 'source_scenario')

    def test_case_count(self, obj):
        return obj.test_cases.count()

    def get_urls(self):
        return [
            path('generate/', self.admin_site.admin_view(self.generate_view), name='learn_codingchallenge_generate'),
        ] + super().get_urls()

    def _unique_slug(self, title):
        base = slugify(title)[:50] or 'coding-challenge'
        slug = base
        n = 2
        while CodingChallenge.objects.filter(slug=slug).exists():
            slug = f'{base}-{n}'
            n += 1
        return slug

    def generate_view(self, request):
        concepts = Concept.objects.select_related('chapter', 'chapter__topic', 'chapter__book').order_by(
            'chapter__topic__order', 'chapter__difficulty', 'chapter__order', 'order',
        )
        context = {
            **self.admin_site.each_context(request),
            'title': 'Generate a coding challenge from a scenario',
            'concepts': concepts,
            'difficulty_choices': DIFFICULTY_CHOICES,
            'opts': self.model._meta,
        }

        if request.method != 'POST':
            return render(request, 'admin/learn/codingchallenge/generate.html', context)

        action = request.POST.get('action', 'generate')
        scenario = request.POST.get('scenario', '').strip()
        concept_id = request.POST.get('concept_id') or ''
        difficulty_hint = request.POST.get('difficulty_hint') or None
        concept = Concept.objects.filter(id=concept_id).first() if concept_id else None

        context.update({'scenario': scenario, 'concept_id': concept_id, 'difficulty_hint': difficulty_hint})

        if action == 'save':
            draft_raw = request.POST.get('draft', '')
            try:
                draft = json.loads(draft_raw)
                assert draft.get('status') == 'ready'
            except (ValueError, AssertionError):
                messages.error(request, "That draft got lost or corrupted — please generate again.")
                return render(request, 'admin/learn/codingchallenge/generate.html', context)
            if not concept:
                messages.error(request, "Pick a concept to attach this challenge to before saving.")
                context['draft'] = draft
                return render(request, 'admin/learn/codingchallenge/generate.html', context)

            challenge = CodingChallenge.objects.create(
                concept=concept,
                slug=self._unique_slug(draft['title']),
                title=draft['title'],
                prompt=draft['prompt'],
                constraints=draft.get('constraints', ''),
                starter_code=draft.get('starter_code', ''),
                difficulty=draft.get('difficulty', 1),
                source_scenario=scenario,
            )
            for i, tc in enumerate(draft.get('test_cases', [])):
                TestCase.objects.create(
                    challenge=challenge, stdin=tc.get('stdin', ''),
                    expected_output=tc.get('expected_output', ''),
                    is_sample=bool(tc.get('is_sample')), order=i,
                )
            messages.success(request, f'Created "{challenge.title}" with {challenge.test_cases.count()} test cases.')
            return redirect(reverse('admin:learn_codingchallenge_change', args=[challenge.pk]))

        # action == 'generate' (either the first attempt, or a resubmission
        # after the admin added clarifying-question answers into the same
        # scenario textarea)
        if not scenario:
            messages.error(request, "Write a scenario first.")
            return render(request, 'admin/learn/codingchallenge/generate.html', context)

        try:
            result = llm.generate_coding_challenge(scenario, concept=concept, difficulty_hint=difficulty_hint)
        except llm.LLMError as exc:
            messages.error(request, str(exc))
            return render(request, 'admin/learn/codingchallenge/generate.html', context)

        if result['status'] == 'needs_clarification':
            context['clarification'] = result
        else:
            context['draft'] = result
            context['draft_json'] = json.dumps(result)
        return render(request, 'admin/learn/codingchallenge/generate.html', context)


@admin.register(CodingAttempt)
class CodingAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'challenge', 'score', 'xp_awarded', 'is_perfect', 'created_at')
    list_filter = ('is_perfect', 'challenge__concept__chapter__topic', 'challenge__concept__chapter__book')
    readonly_fields = ('user', 'challenge', 'code', 'score', 'xp_awarded', 'is_perfect', 'detail', 'created_at')


class FlawPartInline(admin.TabularInline):
    model = FlawPart
    extra = 0
    fields = ('order', 'key', 'kind', 'label', 'sublabel', 'is_flaw', 'geometry')
    show_change_link = True


@admin.register(FlawChallenge)
class FlawChallengeAdmin(admin.ModelAdmin):
    """Parts are listed inline for an overview; open a part to edit its
    explanation and, for a planted flaw, its candidate reasons."""
    list_display = ('title', 'concept', 'flaw_count')
    inlines = [FlawPartInline]

    def flaw_count(self, obj):
        return obj.parts.filter(is_flaw=True).count()


class FlawReasonInline(admin.TabularInline):
    model = FlawReason
    extra = 1


@admin.register(FlawPart)
class FlawPartAdmin(admin.ModelAdmin):
    list_display = ('label', 'challenge', 'kind', 'is_flaw')
    list_filter = ('challenge', 'kind', 'is_flaw')
    inlines = [FlawReasonInline]


@admin.register(TrafficChallenge)
class TrafficChallengeAdmin(admin.ModelAdmin):
    """`params` feeds both copies of the load model (learn/traffic.py and
    learn/static/learn/traffic_model.js); its shape is documented above
    seed_games.TRAFFIC_CHALLENGES."""
    list_display = ('title', 'concept')


@admin.register(TrafficAttempt)
class TrafficAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'challenge', 'score', 'xp_awarded', 'is_perfect', 'created_at')
    list_filter = ('is_perfect', 'challenge')
    readonly_fields = ('user', 'challenge', 'score', 'xp_awarded', 'is_perfect', 'detail', 'created_at')


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
admin.site.register(FlawAttempt)
