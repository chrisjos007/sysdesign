from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

import json

from . import traffic
from .management.commands.seed_games import FLAW_CHALLENGES, TRAFFIC_CHALLENGES
from .models import (
    Book, Chapter, Concept, FlawAttempt, FlawChallenge, FlawPart, FlawReason, Topic,
    TrafficAttempt, TrafficChallenge, UserBadge,
)


class SpotTheFlawTests(TestCase):
    """A three-part diagram: one healthy box, one flawed box, one flawed arrow."""

    def setUp(self):
        book = Book.objects.create(slug='b', title='Book')
        topic = Topic.objects.create(slug='t', title='Topic')
        self.chapter = Chapter.objects.create(book=book, topic=topic, slug='c', title='Chapter', unlock_level=1)
        concept = Concept.objects.create(chapter=self.chapter, slug='k', title='Concept', summary='s')
        self.challenge = FlawChallenge.objects.create(concept=concept, slug='flaw', title='Flawed', prompt='Find them.')
        FlawPart.objects.create(
            challenge=self.challenge, key='cache', label='Cache', geometry={'x': 0, 'y': 0, 'w': 100, 'h': 50},
            explanation='HEALTHY-NOTE', order=0,
        )
        self.box = FlawPart.objects.create(
            challenge=self.challenge, key='db', label='Database', sublabel='1 instance', is_flaw=True,
            geometry={'x': 200, 'y': 0, 'w': 100, 'h': 50}, order=1,
        )
        self.arrow = FlawPart.objects.create(
            challenge=self.challenge, key='e-db', kind=FlawPart.EDGE, label='Cache to Database', is_flaw=True,
            geometry={'d': 'M100 25 L200 25'}, order=2,
        )
        self.box_right = FlawReason.objects.create(part=self.box, text='BOX-RIGHT', is_correct=True)
        self.box_wrong = FlawReason.objects.create(part=self.box, text='BOX-WRONG')
        self.arrow_right = FlawReason.objects.create(part=self.arrow, text='ARROW-RIGHT', is_correct=True)
        FlawReason.objects.create(part=self.arrow, text='ARROW-WRONG')

        self.user = get_user_model().objects.create_user('player', password='pw-for-tests-only')
        self.client.force_login(self.user)
        self.page_url = reverse('learn:flaw_challenge', args=['flaw'])
        self.move_url = reverse('learn:flaw_move', args=['flaw'])
        self.client.get(self.page_url)  # starts the run

    def move(self, **data):
        return self.client.post(self.move_url, data)

    def test_page_draws_every_part_without_revealing_answers(self):
        html = self.client.get(self.page_url).content.decode()
        for key in ('cache', 'db', 'e-db'):
            self.assertIn(f'data-key="{key}"', html)
        for secret in ('HEALTHY-NOTE', 'BOX-RIGHT', 'BOX-WRONG', 'ARROW-RIGHT', 'is_flaw'):
            self.assertNotIn(secret, html)

    def test_healthy_tap_costs_once_and_reveals_why(self):
        body = self.move(action='inspect', part='cache').json()
        self.assertEqual(body['result'], {'verdict': 'fine', 'points': -10})
        self.assertEqual(body['snapshot']['parts']['cache'], {'state': 'fine', 'note': 'HEALTHY-NOTE'})
        again = self.move(action='inspect', part='cache').json()
        self.assertEqual(again['result']['points'], 0)
        self.assertEqual(again['snapshot']['score'], -10)

    def test_flawed_part_offers_reasons_without_marking_the_right_one(self):
        body = self.move(action='inspect', part='db').json()
        self.assertEqual(body['result']['verdict'], 'suspect')
        self.assertEqual({r['text'] for r in body['result']['reasons']}, {'BOX-RIGHT', 'BOX-WRONG'})
        self.assertTrue(all(set(r) == {'id', 'text', 'tried'} for r in body['result']['reasons']))
        self.assertNotIn('db', body['snapshot']['parts'])
        self.assertEqual(body['snapshot']['score'], 0)

    def test_wrong_reason_costs_once_and_is_crossed_off(self):
        body = self.move(action='answer', part='db', reason=self.box_wrong.id).json()
        self.assertEqual(body['result']['points'], -10)
        tried = {r['text']: r['tried'] for r in body['result']['reasons']}
        self.assertEqual(tried, {'BOX-RIGHT': False, 'BOX-WRONG': True})
        again = self.move(action='answer', part='db', reason=self.box_wrong.id).json()
        self.assertEqual(again['result']['points'], 0)
        self.assertEqual(again['snapshot']['score'], -10)

    def test_finding_the_last_flaw_closes_the_review(self):
        self.move(action='inspect', part='cache')
        self.move(action='answer', part='db', reason=self.box_wrong.id)
        first = self.move(action='answer', part='db', reason=self.box_right.id).json()
        self.assertIsNone(first['finished'])
        self.assertEqual(first['snapshot']['parts']['db'], {'state': 'found', 'note': 'BOX-RIGHT'})

        last = self.move(action='answer', part='e-db', reason=self.arrow_right.id).json()
        self.assertEqual(last['finished']['score'], 25 * 2 - 10 - 10)
        self.assertFalse(last['finished']['is_perfect'])
        self.assertTrue(last['snapshot']['done'])
        attempt = FlawAttempt.objects.get(user=self.user)
        self.assertEqual((attempt.score, attempt.xp_awarded), (30, 30))
        self.assertEqual(attempt.detail['healthy_taps'], ['Cache'])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.xp, 30)

    def test_clean_run_earns_bonus_and_badge(self):
        self.move(action='answer', part='db', reason=self.box_right.id)
        body = self.move(action='answer', part='e-db', reason=self.arrow_right.id).json()
        self.assertTrue(body['finished']['is_perfect'])
        self.assertEqual(body['finished']['score'], 25 * 2 + 25)
        self.assertEqual(body['snapshot']['score'], 75)
        self.assertIn('Flaw Finder', body['finished']['new_badges'])
        self.assertTrue(UserBadge.objects.filter(user=self.user, badge__slug='flaw_finder').exists())

    def test_finishing_early_charges_for_missed_flaws(self):
        self.move(action='answer', part='db', reason=self.box_right.id)
        body = self.move(action='finish').json()
        self.assertEqual(body['finished']['score'], 25 - 15)
        self.assertEqual(body['finished']['detail']['missed'], ['Cache to Database'])
        self.assertEqual(body['snapshot']['parts']['e-db'], {'state': 'missed', 'note': 'ARROW-RIGHT'})
        self.assertEqual(body['snapshot']['parts']['cache']['state'], 'unchecked')

    def test_negative_score_awards_no_xp(self):
        self.move(action='inspect', part='cache')
        body = self.move(action='finish').json()
        self.assertEqual(body['finished']['score'], -10 - 15 * 2)
        self.assertEqual(body['finished']['xp_awarded'], 0)

    def test_closed_review_refuses_moves_until_reloaded(self):
        self.move(action='finish')
        self.assertEqual(self.move(action='inspect', part='db').status_code, 409)
        self.client.get(self.page_url)
        body = self.move(action='inspect', part='cache').json()
        self.assertEqual(body['snapshot']['score'], -10)
        self.assertFalse(body['snapshot']['done'])

    def test_reloading_mid_review_keeps_penalties(self):
        self.move(action='inspect', part='cache')
        page = self.client.get(self.page_url)
        self.assertEqual(page.context['snapshot']['score'], -10)
        self.assertEqual(page.context['snapshot']['parts']['cache']['state'], 'fine')

    def test_moves_that_do_not_fit_the_diagram_are_rejected(self):
        self.assertEqual(self.move(action='inspect', part='nope').status_code, 400)
        self.assertEqual(self.move(action='answer', part='cache', reason=self.box_right.id).status_code, 400)
        self.assertEqual(self.move(action='answer', part='e-db', reason=self.box_right.id).status_code, 400)
        self.assertEqual(self.move(action='answer', part='db', reason='x').status_code, 400)
        self.assertEqual(self.move(action='explode').status_code, 400)
        self.assertEqual(self.client.get(self.move_url).status_code, 405)

    def test_locked_chapter_blocks_play(self):
        self.chapter.unlock_level = 99
        self.chapter.save()
        self.assertRedirects(self.client.get(self.page_url), reverse('learn:dashboard'))
        self.assertEqual(self.move(action='inspect', part='cache').status_code, 403)

    def test_concept_page_lists_the_challenge(self):
        html = self.client.get(reverse('learn:concept_detail', args=['k'])).content.decode()
        self.assertIn(self.page_url, html)
        self.assertIn('Spot the Flaw', html)


class FlawSeedDataTests(TestCase):
    """The seeded diagrams are hand-drawn coordinates; catch typos before they ship."""

    def test_every_challenge_is_well_formed(self):
        for spec in FLAW_CHALLENGES:
            parts = spec['boxes'] + spec['arrows']
            keys = [p['key'] for p in parts]
            self.assertEqual(len(keys), len(set(keys)), spec['slug'])
            flaws = [p for p in parts if 'flaw' in p]
            self.assertTrue(flaws, spec['slug'])
            for p in parts:
                if 'flaw' in p:
                    self.assertGreaterEqual(len(p['flaw']), 2, p['key'])
                    self.assertNotIn('ok', p, p['key'])
                else:
                    self.assertTrue(p.get('ok'), p['key'])
            for b in spec['boxes']:
                x, y, w, h = b['box']
                self.assertTrue(0 <= x and x + w <= spec['width'] and 0 <= y and y + h <= spec['height'], b['key'])
            for a in spec['arrows']:
                self.assertTrue(a['d'].startswith('M'), a['key'])
                if a.get('caption'):
                    self.assertIn('at', a, a['key'])


class TrafficDayTests(TestCase):
    """Runs the seeded URL-shortener day through the finish endpoint."""

    def setUp(self):
        book = Book.objects.create(slug='b', title='Book')
        topic = Topic.objects.create(slug='t', title='Topic')
        self.chapter = Chapter.objects.create(book=book, topic=topic, slug='c', title='Chapter', unlock_level=1)
        concept = Concept.objects.create(chapter=self.chapter, slug='k', title='Concept', summary='s')
        spec = TRAFFIC_CHALLENGES[0]
        self.challenge = TrafficChallenge.objects.create(
            concept=concept, slug='day', title=spec['title'], prompt=spec['prompt'], params=spec['params'])
        self.user = get_user_model().objects.create_user('player', password='pw-for-tests-only')
        self.client.force_login(self.user)
        self.page_url = reverse('learn:traffic_challenge', args=['day'])
        self.finish_url = reverse('learn:traffic_finish', args=['day'])

    def finish(self, plan):
        return self.client.post(self.finish_url, json.dumps({'plan': plan}), content_type='application/json')

    @staticmethod
    def steady(servers, replicas, cache, redirect=302):
        return [[servers, replicas, cache, redirect]] * traffic.TICKS

    def test_page_renders_the_simulator(self):
        html = self.client.get(self.page_url).content.decode()
        self.assertIn('id="tr-params"', html)
        self.assertIn('learn/traffic_model.', html)
        self.assertIn('errors over 1%', html)
        self.assertIn('$1.50/h each · 5,000 req/s each', html)

    def test_starting_design_melts_down(self):
        body = self.finish(self.steady(4, 1, False)).json()
        self.assertEqual(body['detail'], {'breaches': 106, 'spent': 240, 'used_301': False, 'design_changes': 0})
        self.assertEqual(body['score'], 1000 - 106 * 50 - 240)
        self.assertEqual(body['xp_awarded'], 0)
        self.assertFalse(body['is_perfect'])
        self.assertTrue(any('Without a cache' in lesson for lesson in body['lessons']))
        self.assertTrue(any('viral link' in lesson for lesson in body['lessons']))

    def test_clean_day_scales_xp_and_earns_badge(self):
        body = self.finish(self.steady(10, 0, True)).json()
        self.assertEqual(body['detail']['breaches'], 0)
        self.assertEqual(body['score'], 573)
        self.assertTrue(body['is_perfect'])
        self.assertEqual(body['xp_awarded'], 573 // 10 + 25)
        self.assertIn('On Call', body['new_badges'])
        attempt = TrafficAttempt.objects.get(user=self.user)
        self.assertEqual((attempt.score, attempt.xp_awarded, attempt.is_perfect), (573, 82, True))

    def test_a_single_301_tick_costs_the_analytics_penalty(self):
        plan = self.steady(10, 0, True)
        plan[5] = [10, 0, True, 301]
        body = self.finish(plan).json()
        self.assertTrue(body['detail']['used_301'])
        self.assertEqual(body['detail']['design_changes'], 2)
        self.assertFalse(body['is_perfect'])
        self.assertLess(body['score'], 573 - 250 + 5)

    def test_scaling_through_the_day_beats_a_steady_design(self):
        # Cheapest design that holds the SLO at each tick, the way a learner would scale in and out.
        options = [dict(servers=s, replicas=0, cache=True, redirect=302) for s in range(1, 15)]
        plan = []
        for i in range(traffic.TICKS):
            cfg = next(o for o in options if not traffic.simulate_tick(self.challenge.params, i, o)['breach'])
            plan.append([cfg['servers'], 0, True, 302])
        body = self.finish(plan).json()
        self.assertEqual(body['detail']['breaches'], 0)
        self.assertGreater(body['score'], 573)

    def test_plans_that_do_not_check_out_are_rejected(self):
        good = self.steady(4, 1, False)
        bad_plans = [
            good[:-1],                                       # a tick short
            [[15, 1, False, 302]] + good[1:],                # over the server limit
            [[4, 5, False, 302]] + good[1:],                 # over the replica limit
            [[True, 1, False, 302]] + good[1:],              # bool where a count belongs
            [[4, 1, 0, 302]] + good[1:],                     # int where the cache flag belongs
            [[4, 1, False, 303]] + good[1:],                 # not a redirect we model
            [[4, 1, False]] + good[1:],                      # short entry
            'everything',
        ]
        for plan in bad_plans:
            self.assertEqual(self.finish(plan).status_code, 400)
        self.assertEqual(self.client.post(self.finish_url, 'nope', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post(self.finish_url, '{}', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.get(self.finish_url).status_code, 405)
        self.assertFalse(TrafficAttempt.objects.exists())

    def test_locked_chapter_blocks_play(self):
        self.chapter.unlock_level = 99
        self.chapter.save()
        self.assertRedirects(self.client.get(self.page_url), reverse('learn:dashboard'))
        self.assertEqual(self.finish(self.steady(4, 1, False)).status_code, 403)

    def test_concept_page_lists_the_challenge(self):
        html = self.client.get(reverse('learn:concept_detail', args=['k'])).content.decode()
        self.assertIn(self.page_url, html)
        self.assertIn('Traffic Day', html)

    def test_seeded_scenarios_are_consistent(self):
        for spec in TRAFFIC_CHALLENGES:
            p = spec['params']
            start = p['start']
            self.assertTrue(p['limits']['servers'][0] <= start['servers'] <= p['limits']['servers'][1])
            self.assertTrue(p['limits']['replicas'][0] <= start['replicas'] <= p['limits']['replicas'][1])
            self.assertIn(start['redirect'], (301, 302))
            for tick in p['events']:
                self.assertTrue(0 <= int(tick) < traffic.TICKS, tick)
            self.assertTrue(0 <= p['spike']['at_hour'] and p['spike']['at_hour'] + p['spike']['hours'] <= 24)
