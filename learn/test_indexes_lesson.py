from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Attempt, Concept, ConceptMastery, ReviewCard


class IndexesLessonTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_curriculum', stdout=StringIO())
        cls.concept = Concept.objects.get(slug='indexes-query-plans')
        cls.user = get_user_model().objects.create_user('indexes-learner')

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse('learn:concept_detail', args=[self.concept.slug])

    def test_lesson_has_exercises_fallbacks_notes_sources_and_quiz(self):
        response = self.client.get(self.url)
        for text in ('sd-05', 'Same answer. Less data to read.', 'Find the newest open orders',
                     'Read the estimate, then the evidence', 'An index cannot remove 51 round trips',
                     'Study notes', 'Sources', '500 rows', '<noscript>', 'Compare query paths'):
            self.assertContains(response, text)
        for filename in ('indexes_lesson.css', 'indexes_model.js', 'indexes_lesson.js'):
            self.assertContains(response, staticfiles_storage.url('learn/' + filename))
        self.assertContains(response, reverse('learn:concept_quiz', args=[self.concept.slug]))
        for slug in ('latency-throughput', 'concurrency-basics'):
            self.assertContains(response, reverse('learn:concept_detail', args=[slug]))

    def test_assets_are_scoped_to_indexes_lesson(self):
        for slug in ('dns-tcp-tls', 'http-api-design', 'latency-throughput', 'concurrency-basics',
                     'requirements-capacity'):
            response = self.client.get(reverse('learn:concept_detail', args=[slug]))
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'id="indexes-lesson"')
            self.assertNotContains(response, staticfiles_storage.url('learn/indexes_model.js'))

    def test_exploring_does_not_award_mastery(self):
        self.client.get(self.url)
        self.client.get(self.url)
        for model in (Attempt, ConceptMastery, ReviewCard):
            self.assertFalse(model.objects.filter(user=self.user).exists())

    def test_authentication_and_unlock_level_still_apply(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.url), '/accounts/login/?next=' + self.url)
        self.client.force_login(self.user)
        chapter = self.concept.chapter
        chapter.unlock_level = 99
        chapter.save()
        self.assertRedirects(self.client.get(self.url), reverse('learn:dashboard'))
