from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

import json
from unittest import mock

from . import bitbudget, quorum, ring, traffic
from .management.commands.seed_games import (
    BIT_BUDGET_CHALLENGES, FLAW_CHALLENGES, QUORUM_CHALLENGES, RING_CHALLENGES, TRAFFIC_CHALLENGES,
)
from .models import (
    BitBudgetAttempt, BitBudgetChallenge, Book, Chapter, Concept, FlawAttempt, FlawChallenge, FlawPart, FlawReason,
    QuorumAttempt, QuorumChallenge, RingAttempt, RingChallenge, Topic, TrafficAttempt, TrafficChallenge, UserBadge,
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
    """Runs the seeded flash-sale day through the finish endpoint."""

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
    def steady(servers, replicas, cache, browser_cache=False):
        return [[servers, replicas, cache, browser_cache]] * traffic.TICKS

    def test_page_renders_the_simulator(self):
        html = self.client.get(self.page_url).content.decode()
        self.assertIn('id="tr-params"', html)
        self.assertIn('learn/traffic_model.', html)
        self.assertIn('errors over 1%', html)
        self.assertIn('$1.50/h each · 5,000 req/s each', html)

    def test_starting_design_melts_down(self):
        body = self.finish(self.steady(4, 1, False)).json()
        self.assertEqual(body['detail'], {'breaches': 106, 'spent': 240, 'browser_cached': False, 'design_changes': 0})
        self.assertEqual(body['score'], 1000 - 106 * 50 - 240)
        self.assertEqual(body['xp_awarded'], 0)
        self.assertFalse(body['is_perfect'])
        self.assertTrue(any('Without a cache' in lesson for lesson in body['lessons']))
        self.assertTrue(any('featured product' in lesson for lesson in body['lessons']))

    def test_clean_day_scales_xp_and_earns_badge(self):
        body = self.finish(self.steady(10, 0, True)).json()
        self.assertEqual(body['detail']['breaches'], 0)
        self.assertEqual(body['score'], 573)
        self.assertTrue(body['is_perfect'])
        self.assertEqual(body['xp_awarded'], 573 // 10 + 25)
        self.assertIn('On Call', body['new_badges'])
        attempt = TrafficAttempt.objects.get(user=self.user)
        self.assertEqual((attempt.score, attempt.xp_awarded, attempt.is_perfect), (573, 82, True))

    def test_a_single_browser_cached_tick_costs_the_stale_page_penalty(self):
        plan = self.steady(10, 0, True)
        plan[5] = [10, 0, True, True]
        body = self.finish(plan).json()
        self.assertTrue(body['detail']['browser_cached'])
        self.assertTrue(any('stale prices' in lesson for lesson in body['lessons']))
        self.assertEqual(body['detail']['design_changes'], 2)
        self.assertFalse(body['is_perfect'])
        self.assertLess(body['score'], 573 - 250 + 5)

    def test_scaling_through_the_day_beats_a_steady_design(self):
        # Cheapest design that holds the SLO at each tick, the way a learner would scale in and out.
        options = [dict(servers=s, replicas=0, cache=True, browser_cache=False) for s in range(1, 15)]
        plan = []
        for i in range(traffic.TICKS):
            cfg = next(o for o in options if not traffic.simulate_tick(self.challenge.params, i, o)['breach'])
            plan.append([cfg['servers'], 0, True, False])
        body = self.finish(plan).json()
        self.assertEqual(body['detail']['breaches'], 0)
        self.assertGreater(body['score'], 573)

    def test_plans_that_do_not_check_out_are_rejected(self):
        good = self.steady(4, 1, False)
        bad_plans = [
            good[:-1],                                       # a tick short
            [[15, 1, False, False]] + good[1:],              # over the server limit
            [[4, 5, False, False]] + good[1:],               # over the replica limit
            [[True, 1, False, False]] + good[1:],            # bool where a count belongs
            [[4, 1, 0, False]] + good[1:],                   # int where the cache flag belongs
            [[4, 1, False, 1]] + good[1:],                   # int where the browser-cache flag belongs
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
            self.assertIs(type(start['browser_cache']), bool)
            for tick in p['events']:
                self.assertTrue(0 <= int(tick) < traffic.TICKS, tick)
            self.assertTrue(0 <= p['spike']['at_hour'] and p['spike']['at_hour'] + p['spike']['hours'] <= 24)


class QuorumCasinoTests(TestCase):
    """Plays the seeded three-table script through the move endpoint."""

    # The exact chance of each read in the seeded script, as a bet: table 1
    # (strict quorum) is certain, table 2 (R = W = 1) comes in thirds, and
    # table 3 (W = N) hands back a failed write.
    EXACT = [99, 99, 1, 33, 67, 33, 1, 33]

    def setUp(self):
        book = Book.objects.create(slug='b', title='Book')
        topic = Topic.objects.create(slug='t', title='Topic')
        self.chapter = Chapter.objects.create(book=book, topic=topic, slug='c', title='Chapter', unlock_level=1)
        concept = Concept.objects.create(chapter=self.chapter, slug='k', title='Concept', summary='s')
        spec = QUORUM_CHALLENGES[0]
        self.challenge = QuorumChallenge.objects.create(
            concept=concept, slug='casino', title=spec['title'], prompt=spec['prompt'],
            source=spec['source'], tables=spec['tables'])
        self.user = get_user_model().objects.create_user('player', password='pw-for-tests-only')
        self.client.force_login(self.user)
        self.page_url = reverse('learn:quorum_challenge', args=['casino'])
        self.move_url = reverse('learn:quorum_move', args=['casino'])
        self.snap = self.client.get(self.page_url).context['snapshot']  # starts the run

    def move(self, **data):
        return self.client.post(self.move_url, data)

    def act(self, **data):
        body = self.move(**data).json()
        self.snap = body['snapshot']
        return body

    def to_read(self):
        """Plays events until a read is waiting for a bet."""
        while not self.snap['question']:
            self.act(action='next')

    def play(self, bets):
        """Bets each of `bets` on the next read in turn; returns the last response."""
        for pct in bets:
            self.to_read()
            body = self.act(action='bet', pct=pct)
        return body

    def test_page_shows_the_first_table_and_nothing_to_come(self):
        html = self.client.get(self.page_url).content.decode()
        self.assertIn('id="qc-snapshot"', html)
        self.assertIn('Table 1: strict quorum', html)
        self.assertIn('up to +39', html)
        self.assertIn('down to &minus;226', html)
        for later in ('Replica A crashes', 'reads were certain', 'Table 2: fast and loose', '"exact"'):
            self.assertNotIn(later, html)

    def test_scoring_rule(self):
        self.assertEqual((quorum.points(50, True), quorum.points(50, False)), (0, 0))
        self.assertEqual((quorum.points(99, True), quorum.points(99, False)), (39, -226))
        self.assertEqual((quorum.points(1, True), quorum.points(1, False)), (-226, 39))
        self.assertEqual(len(quorum.stakes()), 99)

    def test_certain_read_pays_a_confident_bet(self):
        self.to_read()
        self.assertEqual(self.snap['question'], 'Will this read return x = 2, the last successful write?')
        self.assertIsNone(self.snap['feedback'])
        self.assertEqual(self.move(action='next').status_code, 400)
        body = self.act(action='bet', pct=99)
        self.assertEqual(body['result'], {'verdict': 'yes', 'points': 39})
        self.assertIsNone(self.snap['question'])
        self.assertIn('3 of the 3 possible read sets return x = 2', self.snap['feedback']['text'])
        self.assertEqual(len(self.snap['asked']), 2)
        self.assertEqual(self.snap['score'], 39)
        self.assertIn('Read: returned the last successful write. You bet 99% and scored +39.', self.snap['log'])

    def test_a_read_short_of_R_replicas_fails(self):
        body = self.play([99, 99, 1])
        self.assertEqual(body['result'], {'verdict': 'failed', 'points': 39})
        self.assertIn('Only 1 replica is reachable and R = 2, so the read fails.', self.snap['feedback']['text'])
        self.assertTrue(self.snap['table_over'])
        self.assertIn('availability', self.snap['say'])
        self.act(action='next')
        self.assertEqual((self.snap['table'], self.snap['name'], self.snap['log']), (2, 'Table 2: fast and loose', []))

    def test_the_server_draws_the_read_set(self):
        self.play(self.EXACT[:3])
        with mock.patch('learn.quorum.random.choice', side_effect=lambda sets: sets[-1]):
            body = self.play([33])
        self.assertEqual(body['result']['verdict'], 'no')
        self.assertEqual(self.snap['asked'], ['C'])
        self.assertIn('The read asked C and got x = 1. 1 of the 3 replicas it could ask returns x = 2',
                      self.snap['feedback']['text'])

    def test_a_failed_write_still_lands(self):
        self.play(self.EXACT[:6])
        self.to_read()
        self.assertEqual(self.snap['question'], 'Will this read return x = 1, the last successful write?')
        self.assertIn('Failed: 2 acks, W = 3.', self.snap['log'][-1])
        self.assertEqual([r['val'] for r in self.snap['replicas']], [2, 2, 1])
        self.assertEqual(self.act(action='bet', pct=1)['result'], {'verdict': 'no', 'points': 39})

    def test_moves_that_do_not_fit_are_rejected(self):
        self.assertEqual(self.move(action='bet', pct=50).status_code, 400)  # no read waiting yet
        self.to_read()
        for pct in ('0', '100', '-5', 'x', '', '1000', '50.5'):
            self.assertEqual(self.move(action='bet', pct=pct).status_code, 400, pct)
        self.assertEqual(self.move(action='explode').status_code, 400)
        self.assertEqual(self.client.get(self.move_url).status_code, 405)
        self.assertEqual(self.client.get(self.page_url).context['snapshot']['score'], 0)

    def test_reloading_keeps_the_waiting_read_and_the_draw(self):
        self.to_read()
        page = self.client.get(self.page_url)
        self.assertEqual(page.context['snapshot']['question'], self.snap['question'])
        self.act(action='bet', pct=80)
        self.assertEqual(self.client.get(self.page_url).context['snapshot'], self.snap)
        self.assertEqual(self.move(action='bet', pct=99).status_code, 400)

    def test_calibrated_run_earns_bonus_and_badge(self):
        finished = self.play(self.EXACT)['finished']
        self.assertTrue(self.snap['done'])
        self.assertTrue(finished['is_perfect'])
        self.assertEqual(finished['detail']['calibrated'], 8)
        self.assertEqual(finished['score'], self.snap['score'])
        self.assertEqual(finished['xp_awarded'], max(0, finished['score']) + 25)
        self.assertIn('Card Counter', finished['new_badges'])
        attempt = QuorumAttempt.objects.get(user=self.user)
        self.assertEqual(len(attempt.detail['reads']), 8)
        self.assertEqual(attempt.detail['reads'][0]['table'], 'Table 1: strict quorum')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.xp, finished['xp_awarded'])

    def test_overconfidence_costs_the_bonus_and_negative_scores_earn_no_xp(self):
        with mock.patch('learn.quorum.random.choice', side_effect=lambda sets: sets[-1]):
            finished = self.play([99] * 8)['finished']
        self.assertFalse(finished['is_perfect'])
        self.assertEqual(finished['detail']['calibrated'], 2)
        self.assertLess(finished['score'], 0)
        self.assertEqual(finished['xp_awarded'], 0)
        self.assertFalse(UserBadge.objects.filter(user=self.user, badge__slug='card_counter').exists())

    def test_finished_run_refuses_moves_until_reloaded(self):
        self.play(self.EXACT)
        self.assertEqual(self.move(action='next').status_code, 409)
        fresh = self.client.get(self.page_url).context['snapshot']
        self.assertEqual((fresh['table'], fresh['score'], fresh['done'], fresh['log']), (1, 0, False, []))

    def test_run_from_older_tables_starts_over(self):
        session = self.client.session
        session[f'quorum_run_{self.challenge.id}'] = {'table': 7, 'step': 0, 'bets': [], 'done': False}
        session.save()
        self.assertEqual(self.move(action='next').status_code, 409)
        self.assertEqual(self.client.get(self.page_url).context['snapshot']['table'], 1)

    def test_locked_chapter_blocks_play(self):
        self.chapter.unlock_level = 99
        self.chapter.save()
        self.assertRedirects(self.client.get(self.page_url), reverse('learn:dashboard'))
        self.assertEqual(self.move(action='next').status_code, 403)

    def test_concept_page_lists_the_challenge(self):
        html = self.client.get(reverse('learn:concept_detail', args=['k'])).content.decode()
        self.assertIn(self.page_url, html)
        self.assertIn('Quorum Casino', html)


class QuorumSeedDataTests(TestCase):
    def test_seeded_tables_play(self):
        for spec in QUORUM_CHALLENGES:
            self.assertEqual(quorum.validate_tables(spec['tables']), [], spec['slug'])

    def test_validation_catches_broken_scripts(self):
        table = dict(name='T', N=3, W=2, R=2, outro='o', steps=[
            dict(t='read'),
            dict(t='write', val=1, reach=['A', 'D'], say='s'),
            dict(t='status', set={'A': 'asleep'}, say='s'),
            {'t': 'sync', 'from': 'A', 'to': 'A', 'say': 's'},
            dict(t='shout', say='s'),
        ])
        problems = quorum.validate_tables([table])
        self.assertEqual(len(problems), 5, problems)
        self.assertEqual(quorum.validate_tables([]), ['There must be at least one table.'])


class RingBalancerTests(TestCase):
    """Plays the seeded three-challenge ring through the move endpoint."""

    # From the seed: the four-server ring first balances at 6 virtual nodes
    # each (24 positions, 5 points of memory), and the five-server ring with
    # S5 at twice the capacity first balances at 30 per unit of capacity
    # (180 positions, 36 points). RingSeedDataTests pins these down.
    FIRST_K, BIG_K = 6, 30

    def setUp(self):
        book = Book.objects.create(slug='b', title='Book')
        topic = Topic.objects.create(slug='t', title='Topic')
        self.chapter = Chapter.objects.create(book=book, topic=topic, slug='c', title='Chapter', unlock_level=1)
        concept = Concept.objects.create(chapter=self.chapter, slug='k', title='Concept', summary='s')
        spec = RING_CHALLENGES[0]
        self.challenge = RingChallenge.objects.create(
            concept=concept, slug='ring', title=spec['title'], prompt=spec['prompt'],
            source=spec['source'], stages=spec['stages'])
        self.user = get_user_model().objects.create_user('player', password='pw-for-tests-only')
        self.client.force_login(self.user)
        self.page_url = reverse('learn:ring_challenge', args=['ring'])
        self.move_url = reverse('learn:ring_move', args=['ring'])
        self.snap = self.client.get(self.page_url).context['snapshot']  # starts the run

    def move(self, **data):
        return self.client.post(self.move_url, data)

    def act(self, **data):
        body = self.move(**data).json()
        self.snap = body['snapshot']
        return body

    def lock(self, k, weighted=False):
        return self.act(action='lock', k=k, weighted='1' if weighted else '0')

    def to_predictions(self):
        self.lock(self.FIRST_K)
        self.act(action='next')

    def to_big_box(self, answers=(0, 1)):
        self.to_predictions()
        for choice in answers:
            self.act(action='answer', choice=choice)
        self.act(action='next')

    def test_page_draws_the_ring_and_nothing_to_come(self):
        html = self.client.get(self.page_url).content.decode()
        self.assertIn('id="rb-ring"', html)
        self.assertIn('Challenge 1: Even out the load', html)
        self.assertIn('per 5 ring positions', html)
        for later in ('About three quarters', 'S3 is about to crash', 'Challenge 3', '"answer"'):
            self.assertNotIn(later, html)
        data = self.client.get(self.page_url).context['ring_data']
        self.assertEqual(len(data['keys']), ring.KEYS)
        self.assertEqual({sid: len(v) for sid, v in data['vnodes'].items()},
                         {'S1': 200, 'S2': 200, 'S3': 200, 'S4': 200, 'S5': 400})

    def test_unbalanced_lock_in_costs_and_says_why(self):
        body = self.lock(self.FIRST_K - 1)
        self.assertEqual(body['result'], {'verdict': 'unbalanced', 'points': -20})
        self.assertEqual(self.snap['feedback']['text'],
                         'Not balanced yet. The busiest server is still more than 25% over its fair share.')
        self.assertEqual((self.snap['score'], self.snap['cleared'], self.snap['k']), (-20, False, self.FIRST_K - 1))
        self.assertEqual(self.move(action='next').status_code, 400)

    def test_balanced_lock_in_pays_less_the_memory(self):
        body = self.lock(self.FIRST_K)
        self.assertEqual(body['result'], {'verdict': 'balanced', 'points': 95})
        self.assertTrue(self.snap['feedback']['text'].startswith(
            'Balanced with 24 ring positions (6 per server): +100, minus 5 for routing-table memory.'))
        self.assertTrue(self.snap['cleared'])
        self.assertEqual(self.move(action='lock', k=50, weighted='0').status_code, 400)
        self.act(action='next')
        self.assertEqual((self.snap['stage'], self.snap['kind'], self.snap['k']), (2, 'predict', self.FIRST_K))

    def test_predictions_show_the_moves_but_not_the_answer(self):
        self.to_predictions()
        self.assertEqual(self.snap['question']['options'][0], 'About a quarter, only the keys S3 owned')
        self.assertNotIn('answer', self.snap['question'])
        self.assertEqual((self.snap['scheme'], self.snap['down'], self.snap['moved_from']), ('ring', [], None))

        s3 = ring.counts(self.challenge.stages[1], self.FIRST_K)['S3']
        self.assertEqual(self.act(action='answer', choice=0)['result'], {'verdict': 'right', 'points': 50})
        self.assertIn(f'Right: about a quarter, only the keys S3 owned. {s3} of 2,000 keys', self.snap['feedback']['text'])
        self.assertEqual((self.snap['down'], self.snap['moved_from']), (['S3'], {'scheme': 'ring', 'down': []}))
        self.assertIn('Now the same crash under hash(key) % N.', self.snap['text'])

        self.assertEqual(self.act(action='answer', choice=0)['result'], {'verdict': 'wrong', 'points': -25})
        self.assertTrue(self.snap['feedback']['text'].startswith(
            'Not quite. The answer is about three quarters: 1,502 of 2,000 keys (75.1%) changed server'))
        self.assertEqual((self.snap['scheme'], self.snap['cleared'], self.snap['question']), ('mod', True, None))
        self.assertEqual(self.snap['score'], 95 + 50 - 25)
        self.assertEqual(self.move(action='answer', choice=1).status_code, 400)

    def test_a_bigger_box_needs_weighted_virtual_nodes(self):
        self.to_big_box()
        self.assertEqual([s['id'] for s in self.snap['servers']], ['S1', 'S2', 'S3', 'S4', 'S5'])
        self.assertEqual((self.snap['weights'], self.snap['k'], self.snap['down']), (True, self.FIRST_K, []))
        self.lock(self.BIG_K)
        self.assertEqual(self.snap['feedback']['text'], 'Not balanced yet. S5 has twice the memory but the same '
                                                        'number of ring positions as everyone else.')
        body = self.lock(self.BIG_K, weighted=True)
        self.assertEqual(body['result'], {'verdict': 'balanced', 'points': 64})
        self.assertIn('Balanced with 180 ring positions (30 per unit of capacity)', self.snap['feedback']['text'])
        self.assertFalse(body['finished']['is_perfect'])

    def test_clean_run_earns_bonus_and_badge(self):
        self.to_big_box()
        finished = self.lock(self.BIG_K, weighted=True)['finished']
        self.assertTrue(self.snap['done'])
        self.assertEqual(finished['score'], 95 + 50 + 50 + 64)
        self.assertTrue(finished['is_perfect'])
        self.assertEqual(finished['xp_awarded'], 259 // 2 + 25)
        self.assertIn('Ring Master', finished['new_badges'])
        self.assertEqual([s['points'] for s in finished['detail']['stages']], [95, 100, 64])
        attempt = RingAttempt.objects.get(user=self.user)
        self.assertEqual((attempt.score, attempt.xp_awarded, attempt.is_perfect), (259, 154, True))
        self.assertEqual(attempt.detail['stages'][2]['positions'], 180)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.xp, 154)

    def test_negative_score_earns_no_xp(self):
        self.lock(1)
        self.lock(ring.MAX_VNODES)  # 800 positions: 100 - 160
        self.act(action='next')
        self.act(action='answer', choice=2)
        self.act(action='answer', choice=2)
        self.act(action='next')
        finished = self.lock(ring.MAX_VNODES, weighted=True)['finished']
        self.assertEqual(finished['score'], -20 - 60 - 25 - 25 - 140)
        self.assertEqual(finished['xp_awarded'], 0)
        self.assertEqual((finished['detail']['misses'], finished['detail']['wrong']), (1, 2))
        self.assertFalse(UserBadge.objects.filter(user=self.user, badge__slug='ring_master').exists())

    def test_moves_that_do_not_fit_are_rejected(self):
        for k in ('0', '201', '-3', 'x', '', '6.5', '99999'):
            self.assertEqual(self.move(action='lock', k=k, weighted='0').status_code, 400, k)
        self.assertEqual(self.move(action='lock', k=6, weighted='1').status_code, 400)  # no weights here
        self.assertEqual(self.move(action='lock', k=6, weighted='yes').status_code, 400)
        self.assertEqual(self.move(action='answer', choice=0).status_code, 400)  # nothing to predict yet
        self.assertEqual(self.move(action='next').status_code, 400)
        self.assertEqual(self.move(action='explode').status_code, 400)
        self.assertEqual(self.client.get(self.move_url).status_code, 405)
        self.to_predictions()
        for choice in ('3', '-1', 'a', ''):
            self.assertEqual(self.move(action='answer', choice=choice).status_code, 400, choice)
        self.assertEqual(self.client.get(self.page_url).context['snapshot']['score'], 95)

    def test_reloading_keeps_a_miss(self):
        self.lock(1)
        page = self.client.get(self.page_url).context['snapshot']
        self.assertEqual(page, self.snap)
        self.assertEqual((page['score'], page['k']), (-20, 1))

    def test_finished_run_refuses_moves_until_reloaded(self):
        self.to_big_box()
        self.lock(self.BIG_K, weighted=True)
        self.assertEqual(self.move(action='next').status_code, 409)
        fresh = self.client.get(self.page_url).context['snapshot']
        self.assertEqual((fresh['stage'], fresh['score'], fresh['done'], fresh['k']), (1, 0, False, 1))

    def test_run_from_older_stages_starts_over(self):
        session = self.client.session
        session[f'ring_run_{self.challenge.id}'] = {'stage': 7, 'locks': [], 'answers': [], 'done': False}
        session.save()
        self.assertEqual(self.move(action='next').status_code, 409)
        self.assertEqual(self.client.get(self.page_url).context['snapshot']['stage'], 1)

    def test_locked_chapter_blocks_play(self):
        self.chapter.unlock_level = 99
        self.chapter.save()
        self.assertRedirects(self.client.get(self.page_url), reverse('learn:dashboard'))
        self.assertEqual(self.move(action='next').status_code, 403)

    def test_concept_page_lists_the_challenge(self):
        html = self.client.get(reverse('learn:concept_detail', args=['k'])).content.decode()
        self.assertIn(self.page_url, html)
        self.assertIn('Ring Balancer', html)


class RingSeedDataTests(TestCase):
    def test_seeded_stages_play(self):
        for spec in RING_CHALLENGES:
            self.assertEqual(ring.validate_stages(spec['stages']), [], spec['slug'])

    def test_seeded_rings_teach_what_they_say(self):
        first, predict, big = RING_CHALLENGES[0]['stages']
        passes = [k for k in range(1, ring.MAX_VNODES + 1) if ring.is_balanced(first, ring.counts(first, k))]
        self.assertEqual(passes[0], RingBalancerTests.FIRST_K)
        # Whatever balanced ring carries into the crash, the seeded answers hold:
        # nearer a quarter of the keys move on the ring, nearer three quarters under hash % N.
        for k in passes:
            on_ring = sum(1 for a, b in zip(ring.owners(predict, k), ring.owners(predict, k, down=('S3',))) if a != b)
            self.assertLess(on_ring, ring.KEYS / 2, k)
        mod = sum(1 for a, b in zip(ring.owners(predict, 1, scheme='mod'),
                                    ring.owners(predict, 1, scheme='mod', down=('S3',))) if a != b)
        self.assertTrue(ring.KEYS / 2 < mod < ring.KEYS * 7 / 8)
        # Only weighting by capacity balances the bigger box.
        self.assertFalse(any(ring.is_balanced(big, ring.counts(big, k)) for k in range(1, ring.MAX_VNODES + 1)))
        weighted = [k for k in range(1, ring.MAX_VNODES + 1) if ring.is_balanced(big, ring.counts(big, k, True))]
        self.assertEqual(weighted[0], RingBalancerTests.BIG_K)

    def test_validation_catches_broken_stages(self):
        four = [dict(id=f'S{i}', w=1) for i in range(1, 5)]
        stages = [
            dict(t='predict', title='P', text='t', servers=four, questions=[
                dict(ask='a', after='b', scheme='ring', crash='S9', options=['x', 'y'], answer=0),
                dict(ask='a', after='b', scheme='hash', crash='S1', options=['x', 'y'], answer=2),
            ]),
            dict(t='balance', title='B', text='t', servers=four, rule='fairest', within=25, weights=False, done='d'),
            dict(t='balance', title='B', text='t', servers=four, rule='busiest', within=1, weights=False, done='d'),
            dict(t='balance', title='B', text='t', servers=[dict(id='S1', w=0)], rule='busiest', within=25,
                 weights=False, done='d'),
            dict(t='shuffle', title='S', text='t', servers=[dict(id=f'X{i}', w=1) for i in range(3)]),
        ]
        problems = ring.validate_stages(stages)
        self.assertEqual(len(problems), 8, problems)
        self.assertEqual(ring.validate_stages([]), ['There must be at least one stage.'])


class BitBudgetTests(TestCase):
    """Plays the seeded four-round Bit Budget through the move endpoint."""

    # The only splits that meet Specs 1 and 2 (BitBudgetSeedDataTests checks
    # they're the only ones): Spec 1 from the 2026 epoch, Spec 2 from 2015.
    SPEC1 = ('41,3,8,11', 2026)
    SPEC2 = ('42,2,10,9', 2015)

    def setUp(self):
        book = Book.objects.create(slug='b', title='Book')
        topic = Topic.objects.create(slug='t', title='Topic')
        self.chapter = Chapter.objects.create(book=book, topic=topic, slug='c', title='Chapter', unlock_level=1)
        concept = Concept.objects.create(chapter=self.chapter, slug='k', title='Concept', summary='s')
        spec = BIT_BUDGET_CHALLENGES[0]
        self.challenge = BitBudgetChallenge.objects.create(
            concept=concept, slug='bits', title=spec['title'], prompt=spec['prompt'],
            source=spec['source'], stages=spec['stages'])
        self.user = get_user_model().objects.create_user('player', password='pw-for-tests-only')
        self.client.force_login(self.user)
        self.page_url = reverse('learn:bit_budget_challenge', args=['bits'])
        self.move_url = reverse('learn:bit_budget_move', args=['bits'])
        self.snap = self.client.get(self.page_url).context['snapshot']  # starts the run

    def move(self, **data):
        return self.client.post(self.move_url, data)

    def act(self, **data):
        body = self.move(**data).json()
        self.snap = body['snapshot']
        return body

    def check(self, bits, epoch):
        return self.act(action='check', bits=bits, epoch=epoch)

    def to_clock(self):
        self.check(*self.SPEC1)
        self.act(action='next')
        self.check(*self.SPEC2)
        self.act(action='next')
        self.act(action='claim')
        self.act(action='next')

    def test_page_shows_the_spec_but_not_whether_it_can_be_met(self):
        response = self.client.get(self.page_url)
        html = response.content.decode()
        self.assertIn('Spec 1: Tracking events', html)
        self.assertIn('per failed check or wrong call', html)
        for later in ('A merger', 'Clock trouble', 'Hold it until', 'Counting from launch', 'coarser clock tick',
                      '"why"', '"answer"', '"start"'):
            self.assertNotIn(later, html)
        snap = response.context['snapshot']
        self.assertFalse({'why', 'possible'} & set(snap))
        self.assertEqual((snap['width'], snap['budget'], snap['bits'], snap['epoch']), (64, 63, [40, 4, 8, 11], 1970))
        self.assertEqual(snap['fields'][0], {'key': 'ts', 'name': 'Timestamp', 'until': 2090})
        self.assertEqual([e['year'] for e in snap['epochs']], [1970, 2026])

    def test_failed_check_costs_and_names_the_shortfall(self):
        body = self.check('40,4,8,11', 1970)
        self.assertEqual(body['result'], {'verdict': 'short', 'points': -25})
        self.assertEqual(self.snap['feedback']['text'], 'Not yet: the timestamp runs out in 2004, before 2090.')
        self.assertEqual(self.snap['checked'], {'bits': [40, 4, 8, 11], 'epoch': 1970, 'marks': [False, True, True, True]})
        self.check('42,2,8,10', 1970)
        self.assertEqual(self.snap['feedback']['text'],
                         'Not yet: region gives 4 regions, short of 6; '
                         'counter gives 1,024 IDs per ms per worker, short of 1,500.')
        self.assertEqual((self.snap['score'], self.snap['cleared'], self.snap['bits']), (-50, False, [42, 2, 8, 10]))
        self.assertEqual(self.move(action='next').status_code, 400)

    def test_spec_one_needs_the_launch_epoch(self):
        self.check('41,3,8,11', 1970)
        self.assertEqual(self.snap['feedback']['text'], 'Not yet: the timestamp runs out in 2039, before 2090.')
        body = self.check(*self.SPEC1)
        self.assertEqual(body['result'], {'verdict': 'met', 'points': 100})
        self.assertTrue(self.snap['feedback']['text'].startswith('Spec met: +100. Counting from launch'))
        self.assertEqual((self.snap['score'], self.snap['cleared']), (75, True))
        self.assertEqual(self.move(action='claim').status_code, 400)
        self.act(action='next')
        self.assertEqual((self.snap['stage'], self.snap['bits'], self.snap['epoch'], self.snap['checked']),
                         (2, [39, 4, 11, 9], 2015, None))

    def test_wrong_call_costs_and_hints(self):
        body = self.act(action='claim')
        self.assertEqual(body['result'], {'verdict': 'wrong', 'points': -25})
        self.assertEqual(self.snap['feedback']['text'], 'It can be done. Keep adjusting the fields, and look at the epoch.')
        self.check(*self.SPEC1)
        self.act(action='next')
        self.act(action='claim')
        self.assertEqual(self.snap['feedback']['text'], 'It can be done. Keep adjusting the fields.')

    def test_a_fixed_epoch_is_enforced(self):
        self.check(*self.SPEC1)
        self.act(action='next')
        self.assertEqual(self.move(action='check', bits='41,2,10,9', epoch=2026).status_code, 400)
        self.check('41,2,10,9', 2015)
        self.assertEqual(self.snap['feedback']['text'], 'Not yet: the timestamp runs out in 2084, before 2090.')
        self.assertEqual(self.check(*self.SPEC2)['result'], {'verdict': 'met', 'points': 100})

    def test_spotting_the_impossible_spec(self):
        self.check(*self.SPEC1)
        self.act(action='next')
        self.check(*self.SPEC2)
        self.act(action='next')
        self.assertEqual((self.snap['width'], self.snap['signed'], self.snap['budget']), (53, False, 53))
        self.check('41,1,6,5', 2026)
        self.assertEqual(self.snap['feedback']['text'],
                         'Not yet: counter gives 32 IDs per ms per worker, short of 100.')
        body = self.act(action='claim')
        self.assertEqual(body['result'], {'verdict': 'right', 'points': 100})
        self.assertIn("Right, it can't be done: +100. Region, worker and counter need at least 1 + 6 + 7 = 14 bits. "
                      'The timestamp needs 41 bits to reach 2066 even from 2026, and 40 bits run out in 2060. '
                      "That's 55 bits against a budget of 53.", self.snap['feedback']['text'])

    def test_clock_questions_hide_the_answer_until_answered(self):
        self.to_clock()
        self.assertEqual((self.snap['stage'], self.snap['kind'], self.snap['answered']), (4, 'clock', None))
        question = self.snap['question']
        self.assertEqual((question['n'], question['of']), (1, 2))
        self.assertNotIn('answer', question)
        self.assertNotIn('after', question)

        self.assertEqual(self.act(action='answer', choice=0)['result'], {'verdict': 'wrong', 'points': -25})
        self.assertTrue(self.snap['feedback']['text'].startswith(
            'Not quite. Hold the request until the clock passes 05.208.'))
        self.assertEqual((self.snap['answered']['choice'], self.snap['answered']['answer']), (0, 2))
        self.assertEqual((self.snap['question']['n'], self.snap['cleared']), (2, False))
        self.assertNotIn('answer', self.snap['question'])

        self.assertEqual(self.act(action='answer', choice=1)['result'], {'verdict': 'right', 'points': 50})
        self.assertTrue(self.snap['feedback']['text'].startswith('Right. The delivery comes first.'))
        self.assertEqual((self.snap['question'], self.snap['cleared'], self.snap['done']), (None, True, True))
        self.assertEqual(self.snap['score'], 300 - 25 + 50)

    def test_clean_run_earns_bonus_and_badge(self):
        self.to_clock()
        self.act(action='answer', choice=2)
        finished = self.act(action='answer', choice=1)['finished']
        self.assertEqual(finished['score'], 400)
        self.assertTrue(finished['is_perfect'])
        self.assertEqual(finished['xp_awarded'], 400 // 4 + 25)
        self.assertIn('Bit Packer', finished['new_badges'])
        lines = finished['detail']['stages']
        self.assertEqual([line['points'] for line in lines], [100, 100, 100, 100])
        self.assertEqual([line.get('how') for line in lines], ['check', 'check', 'claim', None])
        self.assertEqual((lines[0]['bits'], lines[0]['epoch']), ([41, 3, 8, 11], 2026))
        attempt = BitBudgetAttempt.objects.get(user=self.user)
        self.assertEqual((attempt.score, attempt.xp_awarded, attempt.is_perfect), (400, 125, True))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.xp, 125)

    def test_negative_score_earns_no_xp(self):
        for _ in range(12):
            self.check('40,4,8,11', 1970)
        self.act(action='claim')
        self.check(*self.SPEC1)
        self.act(action='next')
        self.check(*self.SPEC2)
        self.act(action='next')
        self.check('41,1,6,5', 2026)
        self.act(action='claim')
        self.act(action='next')
        self.act(action='answer', choice=0)
        finished = self.act(action='answer', choice=0)['finished']
        self.assertEqual(finished['score'], -300 - 25 + 100 + 100 - 25 + 100 - 50)
        self.assertEqual(finished['xp_awarded'], 0)
        detail = finished['detail']
        self.assertEqual((detail['failed'], detail['wrong_calls'], detail['wrong']), (13, 1, 2))
        self.assertFalse(finished['is_perfect'])
        self.assertFalse(UserBadge.objects.filter(user=self.user, badge__slug='bit_packer').exists())

    def test_moves_that_do_not_fit_are_rejected(self):
        for bits in ('41,3,8,12', '41,3,8', '41,3,8,11,0', '0,3,8,11', '-1,3,8,11', '41,3,x,11', '',
                     '41;3;8;11', '041,3,8,11', '41, 3,8,11', '1.5,3,8,11'):
            self.assertEqual(self.move(action='check', bits=bits, epoch=2026).status_code, 400, bits)
        for epoch in ('2000', 'x', '', '20266'):
            self.assertEqual(self.move(action='check', bits='41,3,8,11', epoch=epoch).status_code, 400, epoch)
        self.assertEqual(self.move(action='answer', choice=0).status_code, 400)  # no question yet
        self.assertEqual(self.move(action='next').status_code, 400)
        self.assertEqual(self.move(action='explode').status_code, 400)
        self.assertEqual(self.client.get(self.move_url).status_code, 405)
        self.to_clock()
        for choice in ('4', '-1', 'a', ''):
            self.assertEqual(self.move(action='answer', choice=choice).status_code, 400, choice)
        self.assertEqual(self.move(action='claim').status_code, 400)
        self.assertEqual(self.move(action='check', bits='41,3,8,11', epoch=2026).status_code, 400)
        self.assertEqual(self.client.get(self.page_url).context['snapshot']['score'], 300)

    def test_reloading_keeps_a_miss(self):
        self.check('40,4,8,11', 1970)
        page = self.client.get(self.page_url).context['snapshot']
        self.assertEqual(page, self.snap)
        self.assertEqual((page['score'], page['bits']), (-25, [40, 4, 8, 11]))

    def test_finished_run_refuses_moves_until_reloaded(self):
        self.to_clock()
        self.act(action='answer', choice=2)
        self.act(action='answer', choice=1)
        self.assertEqual(self.move(action='next').status_code, 409)
        fresh = self.client.get(self.page_url).context['snapshot']
        self.assertEqual((fresh['stage'], fresh['score'], fresh['done'], fresh['bits']), (1, 0, False, [40, 4, 8, 11]))

    def test_run_from_older_stages_starts_over(self):
        session = self.client.session
        session[f'bits_run_{self.challenge.id}'] = {'stage': 9, 'moves': [], 'done': False}
        session.save()
        self.assertEqual(self.move(action='next').status_code, 409)
        self.assertEqual(self.client.get(self.page_url).context['snapshot']['stage'], 1)

    def test_locked_chapter_blocks_play(self):
        self.chapter.unlock_level = 99
        self.chapter.save()
        self.assertRedirects(self.client.get(self.page_url), reverse('learn:dashboard'))
        self.assertEqual(self.move(action='next').status_code, 403)

    def test_concept_page_lists_the_challenge(self):
        html = self.client.get(reverse('learn:concept_detail', args=['k'])).content.decode()
        self.assertIn(self.page_url, html)
        self.assertIn('Bit Budget', html)


class BitBudgetSeedDataTests(SimpleTestCase):
    def setUp(self):
        self.spec1, self.spec2, self.spec3, self.clock = BIT_BUDGET_CHALLENGES[0]['stages']

    def working_splits(self, stage):
        """Every (split, epoch) that meets the stage, by brute force."""
        n, budget = len(stage['fields']), bitbudget.budget(stage)
        found = []

        def walk(prefix, left):
            if len(prefix) == n:
                for epoch in bitbudget.epochs(stage):
                    if all(bitbudget.passes(f, b, epoch) for f, b in zip(stage['fields'], prefix)):
                        found.append((prefix, epoch))
                return
            for b in range(0 if prefix else 1, left + 1):
                walk(prefix + [b], left - b)
        walk([], budget)
        return found

    def test_seeded_stages_play(self):
        for spec in BIT_BUDGET_CHALLENGES:
            self.assertEqual(bitbudget.validate_stages(spec['stages']), [], spec['slug'])

    def test_specs_teach_what_they_say(self):
        # Spec 1: one split works, and only from launch. From 1970, its 41
        # timestamp bits ran out in 2039.
        self.assertEqual(self.working_splits(self.spec1), [([41, 3, 8, 11], 2026)])
        self.assertEqual(bitbudget.runs_out(1970, 41), 2039)
        self.assertIn('same 41 timestamp bits', self.spec1['done'])
        self.assertIn('ran out in 2039', self.spec1['done'])
        # Spec 2: one split works. From 2015, 41 bits run out in 2084, so the
        # timestamp takes 42 and leaves 21.
        self.assertEqual(self.working_splits(self.spec2), [([42, 2, 10, 9], 2015)])
        self.assertEqual(bitbudget.runs_out(2015, 41), 2084)
        self.assertIn('41 timestamp bits run out in 2084', self.spec2['done'])
        self.assertIn('the 21 bits left', self.spec2['done'])
        # Spec 3 misses by two bits, and a coarser tick can't help: whatever
        # the tick, timestamp and counter must count 100 IDs a millisecond
        # for about 1.26 trillion milliseconds, which takes 47 bits.
        self.assertFalse(bitbudget.possible(self.spec3))
        self.assertEqual(self.working_splits(self.spec3), [])
        self.assertEqual(bitbudget.cheapest(self.spec3), (55, 2026))
        span = bitbudget.span_ms(2026, 2066)
        self.assertEqual(round(span / 1e12, 2), 1.26)
        together = (100 * span - 1).bit_length()
        self.assertEqual(together, 47)
        self.assertGreater(together + bitbudget.min_bits(2) + bitbudget.min_bits(40), 53)
        self.assertIn('1.26 trillion milliseconds', self.spec3['why'])
        self.assertIn('takes 47 bits', self.spec3['why'])
        # Every round opens on a split that doesn't work yet.
        for stage in (self.spec1, self.spec2, self.spec3):
            start = [f['start'] for f in stage['fields']]
            self.assertFalse(all(bitbudget.passes(f, b, stage['epoch']) for f, b in zip(stage['fields'], start)))

    def test_clock_answers_match_their_narration(self):
        backstep, order = self.clock['questions']
        self.assertTrue(backstep['options'][backstep['answer']].startswith('Hold it until the clock passes 05.208'))
        self.assertTrue(backstep['after'].startswith('Hold the request until the clock passes 05.208.'))
        # Worker 9 stamps the earlier event 6 ms fast, so it sorts after the later one.
        handover, delivery = (line['text'][-6:] for line in order['log'])
        self.assertEqual((handover, delivery), ('00.106', '00.102'))
        self.assertTrue(order['options'][order['answer']].startswith('The delivery'))
        self.assertTrue(order['after'].startswith('The delivery comes first.'))

    def test_validation_catches_broken_stages(self):
        ts = dict(key='ts', name='Timestamp', until=2090, start=41)
        count = dict(key='n', name='N', need=4, unit='n', start=2)
        one = [[1970, 'x']]
        stages = [
            dict(t='build', title='A', text='t', width=65, signed=True, epochs=one, epoch=1970, fields=[ts, count], done='d'),
            dict(t='build', title='B', text='t', width=64, signed=True, epochs=one, epoch=2026, fields=[ts, count], done='d'),
            dict(t='build', title='C', text='t', width=64, signed=True, epochs=one, epoch=1970,
                 fields=[dict(ts, until=1960), count], done='d'),
            dict(t='build', title='D', text='t', width=64, signed=True, epochs=one, epoch=1970,
                 fields=[ts, dict(count, start=40)], done='d'),
            dict(t='build', title='E', text='t', width=8, signed=False, epochs=one, epoch=1970,
                 fields=[dict(ts, start=6), count], done='d'),
            dict(t='clock', title='F', text='t', questions=[dict(lead='l', log=[], ask='a', after='b', options=['x'], answer=0)]),
            dict(t='shuffle', title='G', text='t'),
        ]
        problems = bitbudget.validate_stages(stages)
        self.assertEqual(len(problems), 7, problems)
        self.assertIn("stage 5: this spec can't be met, so it needs `why`.", problems)
        self.assertEqual(bitbudget.validate_stages([]), ['There must be at least one stage.'])
