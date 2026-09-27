from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Attempt, Concept, ConceptMastery, ReviewCard


class HttpApiLessonTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_curriculum', stdout=StringIO())
        cls.concept = Concept.objects.get(slug='http-api-design')
        cls.user = get_user_model().objects.create_user('http-learner')

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse('learn:concept_detail', args=[self.concept.slug])

    def test_second_lesson_has_labs_notes_sources_prerequisite_and_existing_quiz(self):
        response = self.client.get(self.url)
        self.assertEqual(self.concept.curriculum['id'], 'sd-02')
        for text in ('Try the contract', 'Send it twice. What changes?', 'Accepted is not finished',
                     'Two editors. One version.', 'Design a report-generation contract',
                     'Replay a request', 'Follow an export', 'Resolve an edit conflict',
                     'Study notes', '5 questions', 'RFC 9110'):
            self.assertContains(response, text)
        self.assertContains(response, reverse('learn:concept_detail', args=['dns-tcp-tls']))
        self.assertContains(response, reverse('learn:concept_quiz', args=[self.concept.slug]))
        for filename in ('http_api_lesson.css', 'http_contract_model.js', 'http_api_lesson.js'):
            self.assertContains(response, staticfiles_storage.url('learn/' + filename))

    def test_unscored_exploration_does_not_create_progress_or_attempts(self):
        self.client.get(self.url)
        self.client.get(self.url)
        self.assertFalse(Attempt.objects.filter(user=self.user).exists())
        self.assertFalse(ReviewCard.objects.filter(user=self.user).exists())
        self.assertFalse(ConceptMastery.objects.filter(user=self.user).exists())

    def test_previous_and_next_lessons_do_not_load_http_assets(self):
        for slug in ('dns-tcp-tls', 'latency-throughput'):
            response = self.client.get(reverse('learn:concept_detail', args=[slug]))
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'id="http-lesson"')
            self.assertNotContains(response, staticfiles_storage.url('learn/http_contract_model.js'))

    def test_authentication_and_locking_still_apply(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.url), '/accounts/login/?next=' + self.url)
        self.client.force_login(self.user)
        chapter = self.concept.chapter
        chapter.unlock_level = 99
        chapter.save()
        self.assertRedirects(self.client.get(self.url), reverse('learn:dashboard'))

    def test_quiz_remains_connected_to_existing_review_and_mastery(self):
        url = reverse('learn:concept_quiz', args=[self.concept.slug])
        response = self.client.get(url)
        count = self.concept.questions.count()
        for _ in range(count):
            question = response.context['next_question']
            ids = list(question.choices.filter(is_correct=True).values_list('id', flat=True))
            response = self.client.post(url, {'question_id': question.pk, 'choice_id': ids})
            self.assertTrue(response.context['result']['is_correct'])
        self.assertTrue(response.context['finished'])
        self.assertEqual(Attempt.objects.filter(user=self.user).count(), count)
        self.assertTrue(ReviewCard.objects.filter(user=self.user, concept=self.concept).exists())
