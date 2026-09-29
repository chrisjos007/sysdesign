"""Traffic Day's load model: one simulated day of a shop's product pages
during a flash sale, in 10-minute ticks, under whatever design the learner
runs at each tick.

The page runs the same model in JavaScript (learn/static/learn/traffic_model.js)
to animate the day. This copy replays the learner's per-tick plan on the
server, so the score that gets filed doesn't depend on anything the browser
reports. The two must stay in step: change one, change the other.

A scenario's numbers (traffic, capacities, prices, the SLO, the spike and the
scoring) come from TrafficChallenge.params; seed_games.TRAFFIC_CHALLENGES
shows the shape. The curve of the day, the latency model and the cache hit
rates are fixed here.
"""
import math

TICKS = 144           # 24 hours of 10-minute ticks
TICKS_PER_HOUR = 6
BROWSER_CACHE_SHARE = 0.65  # share of page views still reaching you once browsers may reuse a page for 5 minutes
CACHE_MISS = 0.15           # everyday page views that miss the server cache
CACHE_MISS_HOT = 0.01       # views of the one featured product page that miss the cache
OVERPROVISIONED_SERVER_SPEND = 250


def _circ(hr, center):
    x = abs(hr - center) % 24
    return min(x, 24 - x)


def _shape(hr):
    """Daily traffic multiplier: an evening peak at 20:00 and a smaller morning bump at 10:00."""
    return (0.35 + 1.15 * math.exp(-(_circ(hr, 20) ** 2) / 32)
            + 0.45 * math.exp(-(_circ(hr, 10) ** 2) / 8))


def _spike(hr, spike):
    start, hours = spike['at_hour'], spike['hours']
    if hr < start or hr >= start + hours:
        return 0
    x = (hr - start) / hours
    ramp = x / 0.15 if x < 0.15 else (1 - x) / 0.25 if x > 0.75 else 1
    return spike['reads_per_sec'] * ramp


def demand(params, i, browser_cache):
    hr = (i + 0.5) / TICKS_PER_HOUR
    f = _shape(hr)
    reads = params['reads_per_sec'] * f
    hot = _spike(hr, params['spike'])
    writes = params['writes_per_sec'] * f
    if browser_cache:
        reads *= BROWSER_CACHE_SHARE
        hot *= BROWSER_CACHE_SHARE
    return {'reads': reads, 'hot': hot, 'writes': writes, 'total': reads + hot + writes}


def _latency(base, util):
    return base / (1 - util) if util < 0.97 else base * 40


def simulate_tick(params, i, cfg):
    """One tick under design `cfg` ({servers, replicas, cache, browser_cache})."""
    d = demand(params, i, cfg['browser_cache'])
    cost = params['hourly_cost']
    u_app = d['total'] / (cfg['servers'] * params['app_capacity'])
    db_reads = (d['reads'] * CACHE_MISS + d['hot'] * CACHE_MISS_HOT) if cfg['cache'] else d['reads'] + d['hot']
    nodes = 1 + cfg['replicas']
    u_db = (d['writes'] + db_reads / nodes) / params['db_capacity']
    touch_db = (db_reads + d['writes']) / d['total']
    mean = _latency(8, u_app) + (1 if cfg['cache'] else 0) + touch_db * _latency(12, u_db)
    p99 = 2.5 * mean
    drop_app = 1 - 1 / u_app if u_app > 1 else 0
    drop_db = 1 - 1 / u_db if u_db > 1 else 0
    err = drop_app + (1 - drop_app) * touch_db * drop_db
    tick_cost = (cfg['servers'] * cost['app'] + (cost['cache'] if cfg['cache'] else 0)
                 + nodes * cost['db']) / TICKS_PER_HOUR
    return {
        'demand': d['total'], 'p99': p99, 'err': err, 'cost': tick_cost,
        'breach': p99 > params['slo']['p99_ms'] or err > params['slo']['error_rate'],
    }


def parse_plan(params, raw):
    """Validates a submitted plan: one [servers, replicas, cache, browser_cache]
    entry per tick. Returns a list of cfg dicts, or None if anything is off."""
    if not isinstance(raw, list) or len(raw) != TICKS:
        return None
    lo_s, hi_s = params['limits']['servers']
    lo_r, hi_r = params['limits']['replicas']
    plan = []
    for entry in raw:
        if not isinstance(entry, list) or len(entry) != 4:
            return None
        servers, replicas, cache, browser_cache = entry
        if not all(type(v) is int for v in (servers, replicas)):
            return None
        if not all(type(v) is bool for v in (cache, browser_cache)):
            return None
        if not (lo_s <= servers <= hi_s and lo_r <= replicas <= hi_r):
            return None
        plan.append({'servers': servers, 'replicas': replicas, 'cache': cache, 'browser_cache': browser_cache})
    return plan


def score_day(params, plan):
    """Replays a whole day and scores it the way the page shows it:
    start − breach penalty per 10 minutes over SLO − dollars spent − the
    stale-page penalty if any tick let browsers keep pages for 5 minutes."""
    ticks = [simulate_tick(params, i, cfg) for i, cfg in enumerate(plan)]
    spent = 0
    for t in ticks:
        spent += t['cost']
    spent = math.floor(spent + 0.5)  # Math.round, not Python's banker's rounding
    breaches = sum(1 for t in ticks if t['breach'])
    browser_cached = any(cfg['browser_cache'] for cfg in plan)
    rules = params['score']
    score = rules['start'] - rules['per_breach'] * breaches - spent - (rules['stale_pages'] if browser_cached else 0)
    return {
        'score': score, 'breaches': breaches, 'spent': spent, 'browser_cached': browser_cached,
        'is_clean': breaches == 0 and not browser_cached,
        'lessons': _lessons(params, plan, ticks, breaches, browser_cached),
    }


def _lessons(params, plan, ticks, breaches, browser_cached):
    spike = params['spike']
    first = int(spike['at_hour'] * TICKS_PER_HOUR)
    last = int((spike['at_hour'] + spike['hours']) * TICKS_PER_HOUR)
    lessons = []
    if sum(1 for cfg in plan if not cfg['cache']) > 40:
        lessons.append(
            'Without a cache, every page view is a database read. This shop serves about '
            f'{round(params["reads_per_sec"] / params["writes_per_sec"])} page views per write, so the database '
            'gives out first.')
    if any(ticks[i]['breach'] for i in range(first, min(last, TICKS - 1) + 1)):
        peak = max(demand(params, i, False)['total'] for i in range(first, last + 1))
        lessons.append(
            f'The featured product pushed demand to about {peak / 1000:.0f}K requests a second, '
            f'{math.ceil(peak / params["app_capacity"])} app servers\' worth. A cache absorbs that one '
            'hot page, but every request still passes through an app server.')
    if browser_cached:
        lessons.append(
            f'Browser caching cut server load because repeat views never reached you, but shoppers saw '
            f'stale prices and stock (−{params["score"]["stale_pages"]}). A copy a browser already holds '
            'cannot be recalled before its max-age runs out (RFC 9111). Keep max-age short, or revalidate, '
            'where freshness matters.')
    server_spend = sum(cfg['servers'] * params['hourly_cost']['app'] / TICKS_PER_HOUR for cfg in plan)
    if server_spend > OVERPROVISIONED_SERVER_SPEND:
        lessons.append(
            'You paid for peak capacity for most of the day. Scaling in overnight is where the '
            'budget goes furthest.')
    if not breaches:
        lessons.append('No SLO breaches all day.')
    return lessons
