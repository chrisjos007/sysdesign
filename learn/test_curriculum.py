import json
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse

from .curriculum import DNS_TCP_TLS, DNS_TCP_TLS_CHAPTER, LEARNING_DIR
from .management.commands.seed_content import BOOKS, TOPICS
from .models import (
    Attempt, Book, Chapter, Choice, CodingChallenge, Concept, ConceptMastery, DesignChallenge, FlawChallenge,
    FlawPart, FlawReason, MatchingPair, OrderingStep, Question, QuorumChallenge, ReviewCard, Topic,
    TrafficChallenge,
)
from .services import XP_CORRECT_BASE, XP_WRONG_PARTICIPATION, get_profile

# Names from the published books the content used to summarize. Seeded text
# must not cite or name them; the curriculum cites primary sources instead.
BOOK_MARKERS = (
    "Insider's Guide", 'Insider’s Guide', 'Grokking', 'Designing Data-Intensive', 'DDIA',
    'Database Internals', 'Pocket Guide', 'Alex Xu', 'Petrov', 'Barrett', 'Educative',
)


class RequestLessonTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_curriculum', stdout=StringIO())
        cls.concept = Concept.objects.get(slug='dns-tcp-tls')
        cls.user = get_user_model().objects.create_user('curriculum-learner')

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse('learn:concept_detail', args=[self.concept.slug])

    def test_matches_first_curriculum_item_and_has_valid_assessments(self):
        catalogue = json.loads((Path(__file__).resolve().parent.parent / 'docs/learning/catalogue.json').read_text(encoding='utf-8'))
        first = catalogue['items'][0]
        self.assertEqual((DNS_TCP_TLS['id'], self.concept.slug, self.concept.title),
                         (first['id'], first['slug'], first['title']))
        self.assertEqual(DNS_TCP_TLS['estimated_minutes'], first['estimated_minutes'])
        self.assertEqual(self.concept.chapter.unlock_level, 1)
        self.assertEqual(self.concept.questions.count(), 6)
        for question in self.concept.questions.all():
            self.assertTrue(question.choices.filter(is_correct=False).exists())
            correct = question.choices.filter(is_correct=True).count()
            self.assertGreater(correct, 0)
            if question.kind == Question.MCQ:
                self.assertEqual(correct, 1)

    def test_page_is_complete_and_browsing_does_not_award_mastery(self):
        response = self.client.get(self.url)
        for text in ('190 ms', 'Trace a timeout', 'Sources and further reading', 'HTTP/3',
                     'The request never arrives', 'The response never arrives', '6 questions'):
            self.assertContains(response, text)
        for asset in ('learn/request_lesson.js', 'learn/request_lesson.css'):
            self.assertContains(response, staticfiles_storage.url(asset))
        self.assertContains(response, 'https://www.rfc-editor.org/rfc/rfc8446')
        self.assertFalse(ConceptMastery.objects.filter(user=self.user).exists())
        self.assertFalse(ReviewCard.objects.filter(user=self.user).exists())
        self.assertFalse(Attempt.objects.filter(user=self.user).exists())

    def test_authentication_and_existing_chapter_gating_are_preserved(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.url), '/accounts/login/?next=' + self.url)
        self.client.force_login(self.user)
        chapter = self.concept.chapter
        chapter.unlock_level = 99
        chapter.save()
        self.assertRedirects(self.client.get(self.url), reverse('learn:dashboard'))

    def test_lesson_is_discoverable_and_first_in_fundamentals(self):
        topic = self.concept.chapter.topic
        Chapter.objects.create(book=self.concept.chapter.book, topic=topic, slug='later', title='Later', order=1)
        self.assertEqual(topic.chapters.first().pk, self.concept.chapter_id)
        self.assertContains(self.client.get(reverse('learn:dashboard')), self.url)
        self.assertContains(self.client.get(reverse('learn:topic_detail', args=[topic.slug])), self.url)

    def test_other_concepts_do_not_load_request_component(self):
        other = Concept.objects.create(chapter=self.concept.chapter, slug='other', title='Other', summary='Other notes')
        response = self.client.get(reverse('learn:concept_detail', args=[other.slug]))
        self.assertNotContains(response, 'request-lesson-data')
        self.assertNotContains(response, staticfiles_storage.url('learn/request_lesson.js'))
        self.assertNotContains(response, staticfiles_storage.url('learn/request_lesson.css'))

    def test_additive_seed_preserves_attempts_and_unrelated_content(self):
        question = self.concept.questions.first()
        attempt = Attempt.objects.create(user=self.user, question=question, is_correct=True, xp_awarded=10)
        choices = list(question.choices.values_list('pk', flat=True))
        review = ReviewCard.objects.create(user=self.user, concept=self.concept)
        book = Book.objects.create(slug='custom-book', title='Custom')
        chapter = Chapter.objects.create(book=book, slug='custom', title='Custom')
        other = Concept.objects.create(chapter=chapter, slug='custom', title='Custom', summary='Custom')
        call_command('seed_curriculum', stdout=StringIO())
        self.assertEqual(Concept.objects.filter(slug=self.concept.slug).count(), 1)
        self.assertEqual(self.concept.questions.count(), 6)
        self.assertEqual(list(question.choices.values_list('pk', flat=True)), choices)
        self.assertTrue(Attempt.objects.filter(pk=attempt.pk, question=question).exists())
        self.assertTrue(ReviewCard.objects.filter(pk=review.pk).exists())
        self.assertTrue(Concept.objects.filter(pk=other.pk).exists())

    def test_full_content_seed_keeps_curriculum_lesson_and_its_attempts(self):
        question = self.concept.questions.first()
        attempt = Attempt.objects.create(user=self.user, question=question, is_correct=True, xp_awarded=10)
        call_command('seed_content', stdout=StringIO())
        self.assertTrue(Concept.objects.filter(pk=self.concept.pk).exists())
        self.assertEqual(self.concept.questions.count(), len(DNS_TCP_TLS_CHAPTER['concept']['questions']))
        self.assertTrue(Attempt.objects.filter(pk=attempt.pk).exists())

    def test_quiz_scores_answers_and_completes_through_existing_review_flow(self):
        url = reverse('learn:concept_quiz', args=[self.concept.slug])
        response = self.client.get(url)
        for index in range(6):
            question = response.context['next_question']
            correct = index != 0
            choices = list(question.choices.filter(is_correct=correct).values_list('pk', flat=True))
            if not correct:
                choices = choices[:1]
            response = self.client.post(url, {'question_id': question.pk, 'choice_id': choices})
            self.assertEqual(response.context['result']['is_correct'], correct)
            self.assertEqual(response.context['result']['xp_awarded'],
                             XP_CORRECT_BASE if correct else XP_WRONG_PARTICIPATION)
        self.assertTrue(response.context['finished'])
        self.assertEqual(response.context['run']['answered'], 6)
        self.assertEqual(response.context['run']['correct'], 5)
        self.assertEqual(Attempt.objects.filter(user=self.user).count(), 6)
        self.assertTrue(ReviewCard.objects.filter(user=self.user, concept=self.concept).exists())


class CurriculumContentTests(TestCase):
    """The full seed: the curriculum replaces the book-derived content."""

    @classmethod
    def setUpTestData(cls):
        # A leftover from the old book-derived seed, which the full seed must remove.
        book = Book.objects.create(slug='system-design-interview-xu', title='Old book', author='Old author')
        topic = Topic.objects.create(slug='distributed-systems-patterns', title='Old topic')
        chapter = Chapter.objects.create(book=book, topic=topic, slug='rate-limiter', title='Old chapter')
        Concept.objects.create(chapter=chapter, slug='rate-limiting-algorithms', title='Old concept', summary='s')
        call_command('seed_content', stdout=StringIO())
        call_command('seed_games', stdout=StringIO())
        cls.items = json.loads((LEARNING_DIR / 'catalogue.json').read_text(encoding='utf-8'))['items']
        cls.user = get_user_model().objects.create_user('curriculum-reader')

    def test_every_catalogue_item_is_a_concept_with_notes_sources_and_a_quiz(self):
        self.assertEqual(len(self.items), 36)
        for item in self.items:
            concept = Concept.objects.get(slug=item['slug'])
            self.assertEqual(concept.curriculum['id'], item['id'])
            self.assertEqual(len(concept.curriculum['sources']), len(item['source_ids']), item['id'])
            self.assertTrue(all(note['body'] for note in concept.notes_sections), item['id'])
            self.assertNotIn('](', json.dumps(concept.notes_sections), item['id'])  # no raw Markdown links
            questions = list(concept.questions.all())
            self.assertGreaterEqual(len(questions), 5, item['id'])
            self.assertEqual(len({q.prompt for q in questions}), len(questions), item['id'])
            for question in questions:
                correct = question.choices.filter(is_correct=True).count()
                self.assertTrue(question.choices.filter(is_correct=False).exists(), question.prompt)
                self.assertEqual(correct, 1) if question.kind == Question.MCQ else self.assertGreater(correct, 0)

    def test_book_derived_content_is_gone(self):
        self.assertEqual(set(Book.objects.values_list('slug', flat=True)), {b['slug'] for b in BOOKS})
        self.assertEqual(set(Topic.objects.values_list('slug', flat=True)), {t['slug'] for t in TOPICS})
        self.assertFalse(Concept.objects.filter(slug='rate-limiting-algorithms').exists())
        self.assertEqual(Concept.objects.count(), len(self.items) + 2)  # plus the Python and OS reference chapters

    def test_seeded_text_names_no_source_book(self):
        texts = [json.dumps(list(model.objects.values()), default=str) for model in (
            Book, Topic, Chapter, Concept, Question, Choice, DesignChallenge, MatchingPair, OrderingStep,
            FlawChallenge, FlawPart, FlawReason, TrafficChallenge, QuorumChallenge,
        )]
        for marker in BOOK_MARKERS:
            self.assertFalse(any(marker in text for text in texts), marker)

    def test_every_lesson_has_a_game_and_every_case_study_a_builder(self):
        for item in self.items:
            concept = Concept.objects.get(slug=item['slug'])
            if item['type'] == 'case_study':
                self.assertTrue(concept.design_challenges.exists(), item['id'])
            else:
                self.assertTrue(any(getattr(concept, games).exists() for games in (
                    'matching_challenges', 'ordering_challenges', 'flaw_challenges',
                    'traffic_challenges', 'quorum_challenges')), item['id'])

    def test_builders_wire_only_required_parts(self):
        for challenge in DesignChallenge.objects.all():
            required = {p.component_type_id for p in challenge.pool_components.filter(is_required=True)}
            distractors = {p.component_type_id for p in challenge.pool_components.filter(is_distractor=True)}
            self.assertTrue(distractors and not required & distractors, challenge.slug)
            wired = set()
            for c in challenge.correct_connections.all():
                wired |= {c.from_component_id, c.to_component_id}
            self.assertEqual(wired, required, challenge.slug)

    def test_matching_and_ordering_items_are_distinct(self):
        for concept in Concept.objects.all():
            for challenge in concept.matching_challenges.all():
                pairs = list(challenge.pairs.values_list('term', 'definition'))
                self.assertEqual(len({t for t, _ in pairs}), len(pairs), challenge.slug)
                self.assertEqual(len({d for _, d in pairs}), len(pairs), challenge.slug)
            for challenge in concept.ordering_challenges.all():
                steps = list(challenge.steps.values_list('text', flat=True))
                self.assertEqual(len(set(steps)), len(steps), challenge.slug)

    def test_lesson_page_shows_objectives_prerequisites_and_sources(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('learn:concept_detail', args=['http-api-design']))
        for text in ('sd-02', 'Beginner', '25', 'Choose a method and response contract for a resource.',
                     'Answer guidance', 'Sources', 'https://www.rfc-editor.org/rfc/rfc9110'):
            self.assertContains(response, text)
        self.assertContains(response, reverse('learn:concept_detail', args=['dns-tcp-tls']))
        self.assertNotContains(response, 'request-lesson-data')

    def test_case_study_page_shows_reference_architecture_and_builder(self):
        profile = get_profile(self.user)
        profile.xp = 10_000
        profile.save()
        self.client.force_login(self.user)
        response = self.client.get(reverse('learn:concept_detail', args=['ticket-booking']))
        for text in ('cs-01', 'case study', 'Buyer → Reservation API: browse or reserve', 'Assessment rubric',
                     'Seat invariant (0 to 4)', 'hypothetical exercise assumptions',
                     reverse('learn:design_challenge', args=['build-ticket-booking'])):
            self.assertContains(response, text)

    def test_stages_unlock_in_order(self):
        levels = [Concept.objects.get(slug=i['slug']).chapter.unlock_level for i in self.items if i['type'] == 'lesson']
        self.assertEqual(levels, sorted(levels))
        self.assertEqual(levels[0], 1)


class SeedContentCleanupTests(TestCase):
    """seed_content removes retired concepts, but not the admin-made coding challenges on them unless asked."""

    def setUp(self):
        book = Book.objects.create(slug='old-book', title='Old book')
        chapter = Chapter.objects.create(book=book, slug='old', title='Old chapter')
        concept = Concept.objects.create(chapter=chapter, slug='old-concept', title='Old concept', summary='s')
        self.coding = CodingChallenge.objects.create(concept=concept, slug='old-code', title='Old code', prompt='p')

    def test_refuses_to_delete_coding_challenges_by_default(self):
        with self.assertRaisesMessage(CommandError, 'old-code (old-concept)'):
            call_command('seed_content', stdout=StringIO())
        self.assertTrue(Concept.objects.filter(slug='old-concept').exists())
        self.assertFalse(Concept.objects.filter(slug='dns-tcp-tls').exists())  # rolled back

    def test_deletes_them_when_asked(self):
        call_command('seed_content', '--delete-coding-challenges', stdout=StringIO())
        self.assertFalse(CodingChallenge.objects.filter(pk=self.coding.pk).exists())
        self.assertFalse(Book.objects.filter(slug='old-book').exists())
