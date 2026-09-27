"""Ring Balancer: 2,000 cache keys on a consistent-hash ring. The learner adds
virtual nodes until the load evens out, predicts how many keys move when a
server crashes (on the ring, then under hash(key) % N), and makes room for a
bigger machine.

This module holds the only copy of the hash. The page gets every key's and
every virtual node's position as data (`ring_data`) and works out owners
itself, so it can redraw the ring as the slider moves. The server works them
out again here to score a lock-in, so the score never rests on the browser.
Both sides use one rule and agree to the key: a key belongs to the first ring
position at or clockwise after it, wrapping past the top, and positions that
tie sort by the server's place in the stage, then by virtual node number.

A run holds only facts: which stage it's at, every lock-in (virtual nodes per
server, and whether they were weighted by capacity) and every prediction. The
score, feedback and scene are rebuilt from those, so a reload changes nothing.

RingChallenge.stages is a list of stages. A server is {'id': 'S1', 'w': 1},
where w is its capacity: a server with w = 2 has twice the fair share. Each
stage is one of

    {'t': 'balance', 'title': ..., 'text': ..., 'servers': [...],
     'rule': 'busiest' or 'every', 'within': 25, 'weights': False,
     'done': ..., 'unweighted_hint': ...}
    {'t': 'predict', 'title': ..., 'text': ..., 'servers': [...],
     'questions': [{'ask': ..., 'scheme': 'ring' or 'mod', 'crash': 'S3',
                    'options': [...], 'answer': 0, 'after': ...}]}

A balance stage clears when a lock-in passes its rule: 'busiest' wants no
server more than `within`% over its fair share, 'every' wants every server
within `within`% of it either way. `weights` offers to give each server
virtual nodes in proportion to w; `unweighted_hint` is the nudge when a
lock-in misses without them. A predict stage runs on the virtual nodes locked
in the balance stage before it. Each question crashes one server under a
scheme ('mod' is hash(key) % N over the servers still up) and asks how many
keys change server; `after` narrates the result.
"""
import math
from bisect import bisect_left
from functools import lru_cache

KEYS = 2000
MAX_VNODES = 200
# The page colours servers with --srv-1 to --srv-5, so a challenge can name at most five.
MAX_SERVERS = 5

BALANCE_POINTS = 100
POSITIONS_PER_POINT = 5   # every ring position is a routing-table entry
MISSED_LOCK = 20
PREDICT_RIGHT = 50
PREDICT_WRONG = 25

RULES = ('busiest', 'every')
SCHEMES = ('ring', 'mod')


def _h32(name):
    """A 32-bit ring position: FNV-1a, then MurmurHash3's finalizer to spread
    the bits. It's the prototype's hash. With it, the seeded four-server ring
    fails its balance test at 1 to 5 virtual nodes each and passes at nearly
    every count from 6 up; MD5 and SHA-1 pass by luck at 2 or 3, then fail
    again up to 15."""
    x = 0x811C9DC5
    for byte in name.encode():
        x = ((x ^ byte) * 0x01000193) & 0xFFFFFFFF
    x ^= x >> 16
    x = (x * 0x85EBCA6B) & 0xFFFFFFFF
    x ^= x >> 13
    x = (x * 0xC2B2AE35) & 0xFFFFFFFF
    return x ^ (x >> 16)


@lru_cache(maxsize=1)
def key_hashes():
    return tuple(_h32(f'user:{i}') for i in range(KEYS))


@lru_cache(maxsize=None)
def _vnodes(sid, count):
    return tuple(_h32(f'{sid}#vnode{j}') for j in range(count))


def _round(x):
    """Halves round up, like JavaScript's Math.round."""
    return math.floor(x + 0.5)


def pct1(n, d):
    """n / d as a percentage with one decimal, halves rounded up (the page does the same)."""
    tenths = (n * 2000 + d) // (2 * d)
    return f'{tenths // 10}.{tenths % 10}'


@lru_cache(maxsize=512)
def _owners(servers, down, k, weighted, scheme):
    """The server that owns each key. `servers` is a tuple of (id, w) in stage order."""
    keys = key_hashes()
    up = [(si, sid, w) for si, (sid, w) in enumerate(servers) if sid not in down]
    if scheme == 'mod':
        return tuple(up[h % len(up)][1] for h in keys)
    points = sorted((pos, si, j) for si, sid, w in up
                    for j, pos in enumerate(_vnodes(sid, k * w if weighted else k)))
    positions = [p[0] for p in points]
    ids = [servers[p[1]][0] for p in points]
    return tuple(ids[bisect_left(positions, h) % len(positions)] for h in keys)


def _servers(stage):
    return tuple((s['id'], s['w']) for s in stage['servers'])


def owners(stage, k, weighted=False, scheme='ring', down=()):
    return _owners(_servers(stage), tuple(down), k, bool(weighted), scheme)


def counts(stage, k, weighted=False, scheme='ring', down=()):
    out = {s['id']: 0 for s in stage['servers']}
    for sid in owners(stage, k, weighted, scheme, down):
        out[sid] += 1
    return out


def positions(stage, k, weighted):
    return sum(k * s['w'] if weighted else k for s in stage['servers'])


def memory_cost(n_positions):
    return _round(n_positions / POSITIONS_PER_POINT)


def is_balanced(stage, have):
    """Whether key counts `have` pass the stage's rule, in whole numbers so
    no rounding can tip a borderline ring either way."""
    total_w = sum(s['w'] for s in stage['servers'])
    within = stage['within']
    for s in stage['servers']:
        load, fair = have[s['id']] * total_w, KEYS * s['w']
        if stage['rule'] == 'busiest':
            if 100 * load > (100 + within) * fair:
                return False
        elif 100 * abs(load - fair) > within * fair:
            return False
    return True


def _lock_result(stage, lock):
    k, weighted = lock['k'], lock['weighted']
    n = positions(stage, k, weighted)
    if is_balanced(stage, counts(stage, k, weighted)):
        cost = memory_cost(n)
        pts = BALANCE_POINTS - cost
        per = 'per unit of capacity' if weighted else 'per server'
        text = (f"Balanced with {n:,} ring positions ({k} {per}): +{BALANCE_POINTS}, minus {cost} "
                f"for routing-table memory. {stage['done']}")
        return {'ok': True, 'points': pts, 'positions': n, 'text': text}
    if stage['weights'] and not weighted and stage.get('unweighted_hint'):
        hint = stage['unweighted_hint']
    elif stage['rule'] == 'busiest':
        hint = f"The busiest server is still more than {stage['within']}% over its fair share."
    else:
        hint = f"Some server is still more than {stage['within']}% off its fair share."
    return {'ok': False, 'points': -MISSED_LOCK, 'positions': n, 'text': f'Not balanced yet. {hint}'}


def _lower_first(text):
    return text[:1].lower() + text[1:]


def _answer_result(stage, q, choice, base):
    question = stage['questions'][q]
    k, weighted = base
    scheme, crash = question['scheme'], question['crash']
    before = owners(stage, k, weighted, scheme)
    after = owners(stage, k, weighted, scheme, down=(crash,))
    moved = sum(1 for a, b in zip(before, after) if a != b)
    right = choice == question['answer']
    answer = _lower_first(question['options'][question['answer']])
    share = f"{moved:,} of {KEYS:,} keys ({pct1(moved, KEYS)}%) changed server, circled on the ring."
    text = f"Right: {answer}. {share}" if right else f"Not quite. The answer is {answer}: {share}"
    return {'right': right, 'points': PREDICT_RIGHT if right else -PREDICT_WRONG, 'moved': moved, 'text': text}


def _carried(stages, run, i):
    """(k, weighted) from the lock-in that cleared the last balance stage before
    stage i; (1, False) if there isn't one."""
    for j in range(i - 1, -1, -1):
        if stages[j]['t'] == 'balance':
            passed = [lk for lk in run['locks'] if lk['stage'] == j]
            if passed:
                return passed[-1]['k'], passed[-1]['weighted']
    return 1, False


def _stage_state(stages, run, i):
    stage = stages[i]
    if stage['t'] == 'balance':
        results = [_lock_result(stage, lk) for lk in run['locks'] if lk['stage'] == i]
        # A cleared stage takes no more lock-ins, so a passing one is always the last.
        cleared = bool(results) and results[-1]['ok']
    else:
        base = _carried(stages, run, i)
        picks = [a['choice'] for a in run['answers'] if a['stage'] == i]
        results = [_answer_result(stage, q, c, base) for q, c in enumerate(picks)]
        cleared = len(results) == len(stage['questions'])
    return {'results': results, 'cleared': cleared}


def _all_results(stages, run):
    return [r for i in range(run['stage'] + 1) for r in _stage_state(stages, run, i)['results']]


def score(stages, run):
    return sum(r['points'] for r in _all_results(stages, run))


def new_run():
    return {'stage': 0, 'locks': [], 'answers': [], 'done': False}


def run_fits(stages, run):
    """False if the stages changed under a saved run (say, a reseed), so it can't be replayed."""
    try:
        if not 0 <= run['stage'] < len(stages):
            return False
        for lk in run['locks']:
            stage = stages[lk['stage']]
            if stage['t'] != 'balance' or not 1 <= lk['k'] <= MAX_VNODES or (lk['weighted'] and not stage['weights']):
                return False
        for i, stage in enumerate(stages):
            picks = [a['choice'] for a in run['answers'] if a['stage'] == i]
            if picks and (stage['t'] != 'predict' or len(picks) > len(stage['questions'])
                          or not all(0 <= c < len(q['options']) for c, q in zip(picks, stage['questions']))):
                return False
        return True
    except (KeyError, TypeError, IndexError):
        return False


def _open_stage(stages, run, kind):
    """The current stage's state if the run can take a `kind` move there, else None."""
    if run['done'] or stages[run['stage']]['t'] != kind:
        return None
    state = _stage_state(stages, run, run['stage'])
    return None if state['cleared'] else state


def _settle(stages, run):
    """Closes the run once the last stage clears."""
    if run['stage'] == len(stages) - 1 and _stage_state(stages, run, run['stage'])['cleared']:
        run['done'] = True


def lock(stages, run, k, weighted):
    """Locks in `k` virtual nodes per server (per unit of capacity if
    `weighted`) on the balance stage in play. Returns None if the move
    doesn't fit."""
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= MAX_VNODES:
        return None
    if _open_stage(stages, run, 'balance') is None:
        return None
    stage = stages[run['stage']]
    if weighted and not stage['weights']:
        return None
    run['locks'].append({'stage': run['stage'], 'k': k, 'weighted': bool(weighted)})
    result = _lock_result(stage, run['locks'][-1])
    _settle(stages, run)
    return {'verdict': 'balanced' if result['ok'] else 'unbalanced', 'points': result['points']}


def answer(stages, run, choice):
    """Answers the waiting prediction with option `choice`. Returns None if
    no prediction is waiting or there's no such option."""
    state = _open_stage(stages, run, 'predict')
    if state is None or isinstance(choice, bool) or not isinstance(choice, int):
        return None
    question = stages[run['stage']]['questions'][len(state['results'])]
    if not 0 <= choice < len(question['options']):
        return None
    run['answers'].append({'stage': run['stage'], 'choice': choice})
    result = _stage_state(stages, run, run['stage'])['results'][-1]
    _settle(stages, run)
    return {'verdict': 'right' if result['right'] else 'wrong', 'points': result['points']}


def advance(stages, run):
    """Opens the next stage once this one is cleared. Returns None otherwise."""
    if run['done'] or run['stage'] >= len(stages) - 1:
        return None
    if not _stage_state(stages, run, run['stage'])['cleared']:
        return None
    run['stage'] += 1
    return {'verdict': 'next'}


def server_order(stages):
    """Every server the challenge names, in order of first appearance; a
    server's place here picks its colour, so it keeps it from stage to stage."""
    order = []
    for stage in stages:
        order += [s['id'] for s in stage['servers'] if s['id'] not in order]
    return order


def ring_data(stages):
    """Every key's ring position, and every virtual node position each server
    could need, for the page to draw and balance the ring with."""
    most = {}
    for stage in stages:
        for s in stage['servers']:
            w = s['w'] if stage['t'] == 'balance' and stage['weights'] else 1
            most[s['id']] = max(most.get(s['id'], 0), MAX_VNODES * w)
    return {'keys': list(key_hashes()), 'vnodes': {sid: list(_vnodes(sid, n)) for sid, n in most.items()}}


def snapshot(stages, run):
    """The public view of a run: the score, the stage in play, the scene to
    draw, and the last move's feedback. It never holds the answer to a
    prediction that's still waiting."""
    i = run['stage']
    stage = stages[i]
    state = _stage_state(stages, run, i)
    results = state['results']
    order = server_order(stages)
    snap = {
        'score': score(stages, run),
        'stage': i + 1, 'stages': len(stages), 'kind': stage['t'], 'title': stage['title'],
        'text': stage['text'],
        'servers': [{'id': s['id'], 'w': s['w'], 'color': order.index(s['id']) + 1} for s in stage['servers']],
        'feedback': {'points': results[-1]['points'], 'text': results[-1]['text']} if results else None,
        'cleared': state['cleared'], 'last': i == len(stages) - 1, 'done': run['done'],
        'question': None, 'moved_from': None,
    }
    if stage['t'] == 'balance':
        locks = [lk for lk in run['locks'] if lk['stage'] == i]
        k, weighted = (locks[-1]['k'], locks[-1]['weighted']) if locks else (_carried(stages, run, i)[0], False)
        snap.update(scheme='ring', down=[], k=k, weighted=weighted, weights=stage['weights'],
                    rule=stage['rule'], within=stage['within'])
    else:
        k, weighted = _carried(stages, run, i)
        questions = stage['questions']
        snap.update(k=k, weighted=weighted, weights=False)
        if results:
            last = questions[len(results) - 1]
            snap.update(scheme=last['scheme'], down=[last['crash']], text=last['after'],
                        moved_from={'scheme': last['scheme'], 'down': []})
        else:
            snap.update(scheme=questions[0]['scheme'], down=[])
        if not state['cleared']:
            q = questions[len(results)]
            snap['question'] = {'ask': q['ask'], 'options': q['options']}
    return snap


def summary(stages, run):
    """One line per stage played, for the verdict and the attempt's detail."""
    lines = []
    for i in range(run['stage'] + 1):
        stage = stages[i]
        results = _stage_state(stages, run, i)['results']
        line = {'title': stage['title'], 'kind': stage['t'], 'points': sum(r['points'] for r in results)}
        if stage['t'] == 'balance':
            locks = [lk for lk in run['locks'] if lk['stage'] == i]
            passed = results[-1]['ok'] if results else False
            line.update(misses=sum(1 for r in results if not r['ok']),
                        positions=results[-1]['positions'] if passed else None,
                        k=locks[-1]['k'] if passed else None,
                        weighted=locks[-1]['weighted'] if passed else None)
        else:
            line.update(right=sum(1 for r in results if r['right']), questions=len(stage['questions']))
        lines.append(line)
    return lines


def validate_stages(stages):
    """Problems with a list of stages, as readable strings; empty if it plays."""
    if not isinstance(stages, list) or not stages:
        return ['There must be at least one stage.']
    problems = []
    balanced_before = False
    named = []
    for i, stage in enumerate(stages):
        where = f'stage {i + 1}'
        if not all(isinstance(stage.get(key), str) and stage.get(key) for key in ('title', 'text')):
            problems.append(f'{where}: needs a title and a text.')
        servers = stage.get('servers') or []
        ids = [s.get('id') for s in servers]
        if (not servers or len(set(ids)) != len(ids) or not all(isinstance(sid, str) and sid for sid in ids)
                or not all(isinstance(s.get('w'), int) and not isinstance(s.get('w'), bool) and s['w'] >= 1
                           for s in servers)):
            problems.append(f'{where}: needs servers with distinct ids and a whole-number capacity w of 1 or more.')
            continue
        named += [sid for sid in ids if sid not in named]
        kind = stage.get('t')
        if kind == 'balance':
            within = stage.get('within')
            if (stage.get('rule') not in RULES or not isinstance(within, int) or not 1 <= within <= 100
                    or not isinstance(stage.get('weights'), bool) or not stage.get('done')):
                problems.append(f"{where}: a balance stage needs a rule ({', '.join(RULES)}), "
                                f"`within` from 1 to 100, `weights` and `done`.")
                continue
            tries = [(k, w) for k in range(1, MAX_VNODES + 1) for w in ((False, True) if stage['weights'] else (False,))]
            if not any(is_balanced(stage, counts(stage, k, w)) for k, w in tries):
                problems.append(f'{where}: no number of virtual nodes balances this ring.')
            balanced_before = True
        elif kind == 'predict':
            if not balanced_before:
                problems.append(f'{where}: a predict stage needs a balance stage before it.')
            questions = stage.get('questions') or []
            if not questions:
                problems.append(f'{where}: needs at least one question.')
            for q, question in enumerate(questions):
                at = f'{where} question {q + 1}'
                options = question.get('options') or []
                if (not question.get('ask') or not question.get('after') or question.get('scheme') not in SCHEMES
                        or question.get('crash') not in ids or len(servers) < 2 or len(options) < 2
                        or not all(isinstance(o, str) and o for o in options)
                        or not isinstance(question.get('answer'), int) or not 0 <= question['answer'] < len(options)):
                    problems.append(f'{at}: needs ask, after, a scheme ({", ".join(SCHEMES)}), a server to crash '
                                    'with one left standing, two or more options and the index of the right one.')
        else:
            problems.append(f'{where}: unknown stage type {kind!r}.')
    if len(named) > MAX_SERVERS:
        problems.append(f'A challenge can name at most {MAX_SERVERS} servers.')
    return problems
