from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Attempt, Concept, ConceptMastery, ReviewCard


class CapacityLessonTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_curriculum', stdout=StringIO())
        cls.concept = Concept.objects.get(slug='requirements-capacity')
        cls.user = get_user_model().objects.create_user('capacity-learner')

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse('learn:concept_detail', args=[self.concept.slug])

    def test_exercises_fallback_sources_and_quiz_are_available(self):
        response = self.client.get(self.url)
        for text in ('sd-06', 'Follow the units', 'Separate three kinds of requirement',
                     'Server count is unknown', '91.25 GB', 'Study notes', '<noscript>',
                     'Estimate the workload', '7.5 GB', 'Service Level Objectives'):
            self.assertContains(response, text)
        for name in ('capacity_lesson.css', 'capacity_model.js', 'capacity_lesson.js'):
            self.assertContains(response, staticfiles_storage.url('learn/' + name))
        for slug in ('http-api-design', 'latency-throughput', 'indexes-query-plans'):
            self.assertContains(response, reverse('learn:concept_detail', args=[slug]))
        self.assertContains(response, reverse('learn:concept_quiz', args=[self.concept.slug]))

    def test_assets_do_not_leak_into_other_lessons(self):
        for slug in ('dns-tcp-tls', 'http-api-design', 'latency-throughput',
                     'concurrency-basics', 'indexes-query-plans'):
            response = self.client.get(reverse('learn:concept_detail', args=[slug]))
            self.assertNotContains(response, 'id="capacity-lesson"')
            self.assertNotContains(response, staticfiles_storage.url('learn/capacity_model.js'))

    def test_browsing_has_no_scoring_side_effects(self):
        self.client.get(self.url)
        self.client.get(self.url)
        for model in (Attempt, ConceptMastery, ReviewCard):
            self.assertFalse(model.objects.filter(user=self.user).exists())

    def test_authentication_and_level_gating(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.url), '/accounts/login/?next=' + self.url)
        self.client.force_login(self.user)
        chapter = self.concept.chapter
        chapter.unlock_level = 99
        chapter.save()
        self.assertRedirects(self.client.get(self.url), reverse('learn:dashboard'))
