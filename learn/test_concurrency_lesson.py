from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Attempt, Concept, ConceptMastery, ReviewCard


class ConcurrencyLessonTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_curriculum', stdout=StringIO())
        cls.concept = Concept.objects.get(slug='concurrency-basics')
        cls.user = get_user_model().objects.create_user('concurrency-learner')

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse('learn:concept_detail', args=[self.concept.slug])

    def test_lesson_has_labs_sources_notes_and_quiz(self):
        response = self.client.get(self.url)
        for text in ('sd-04', 'Two workers. One shared balance.', 'Choose the interleaving',
                     'Separate locks on two servers', 'Protect the last seat',
                     'Study notes', 'Sources', 'Expected after both increments: 12'):
            self.assertContains(response, text)
        for filename in ('concurrency_lesson.css', 'concurrency_model.js', 'concurrency_lesson.js'):
            self.assertContains(response, staticfiles_storage.url('learn/' + filename))
        self.assertContains(response, reverse('learn:concept_quiz', args=[self.concept.slug]))
        self.assertContains(response, reverse('learn:concept_detail', args=['latency-throughput']))

    def test_other_lessons_do_not_load_concurrency_assets(self):
        for slug in ('dns-tcp-tls', 'http-api-design', 'latency-throughput'):
            response = self.client.get(reverse('learn:concept_detail', args=[slug]))
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'id="concurrency-lesson"')
            self.assertNotContains(response, staticfiles_storage.url('learn/concurrency_model.js'))

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
