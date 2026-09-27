"""Quorum Casino: N replicas hold the key x while the learner steps through
writes, crashes and partitions, and before each read bets how likely it is
to return the last successful write.

A run holds only facts: which table it's at, how many of that table's events
have played, and each bet (the chance the learner gave, and which replicas
the read asked). The replicas, the ops log, the odds and the score are
rebuilt from those by replaying the table's script, so a reload changes
nothing. The one random thing, which replicas a read asks, is drawn here
when the bet locks in, never in the browser.

A table (QuorumChallenge.tables) is a dict with `name`, `N`, `W`, `R`,
`outro` and `steps`. Replicas are named A, B, C... up to N. Each step is one of

    {'t': 'write', 'val': 2, 'reach': ['A', 'B'], 'say': ...}
    {'t': 'status', 'set': {'C': 'cut'}, 'say': ...}    # 'up', 'cut' or 'down'
    {'t': 'sync', 'from': 'A', 'to': 'B', 'say': ...}    # anti-entropy copy
    {'t': 'read'}

A write succeeds if it reaches at least W replicas, but the replicas it
reached keep the value either way. A read asks R of the replicas that are up,
picked at random, and keeps the value with the highest version.
"""
import math
import random
from itertools import combinations

# A bet of p that the read returns the last successful write scores
# STAKE * (1 + log2 p) if it does and STAKE * (1 + log2 (1 - p)) if it
# doesn't. Betting 50% always scores 0, and the best bet is the true chance
# (a proper scoring rule), so confidence only pays when it's warranted.
STAKE = 40
MIN_BET, MAX_BET = 1, 99
# A run is calibrated if every bet lands within this many percentage points
# of the exact chance, whatever the draws did.
CALIBRATED_WITHIN = 10

STATES = ('up', 'cut', 'down')


def points(pct, yes):
    """Points for a bet of `pct`% that the read returns the last successful
    write. Halves round up, like JavaScript's Math.round."""
    share = (pct if yes else 100 - pct) / 100
    return math.floor(STAKE * (1 + math.log2(share)) + 0.5)


def stakes():
    """[if yes, if no] for every bet from MIN_BET% to MAX_BET%, so the page
    can preview a bet without a copy of the formula."""
    return [[points(p, True), points(p, False)] for p in range(MIN_BET, MAX_BET + 1)]


def replica_ids(table):
    return [chr(ord('A') + i) for i in range(table['N'])]


def _names(ids):
    ids = list(ids)
    return ids[0] if len(ids) == 1 else ', '.join(ids[:-1]) + ' and ' + ids[-1]


def _signed(v):
    return f'+{v}' if v > 0 else f'−{-v}' if v < 0 else '0'


def _plural(n, word):
    return word if n == 1 else word + 's'


def intro(table):
    name, w, r = table['name'], table['W'], table['R']
    stop = '' if name[-1:] in '.?!' else '.'
    return (f"{name}{stop} The client needs W = {w} {_plural(w, 'acknowledgement')} for a write to "
            f"succeed, and asks R = {r} {_plural(r, 'replica')} on each read.")


def _read_sets(table, reps):
    """The replicas that are up, and every set of R of them a read could ask."""
    up = [i for i in replica_ids(table) if reps[i]['st'] == 'up']
    return up, (list(combinations(up, table['R'])) if len(up) >= table['R'] else [])


def _answer(reps, asked):
    """The replica whose value a read keeps: the highest version, first asked on a tie."""
    return reps[max(asked, key=lambda i: reps[i]['ver'])]


def _resolve(table, reps, latest, step, bet):
    up, sets = _read_sets(table, reps)
    good = sum(1 for s in sets if _answer(reps, s)['ver'] == latest['ver'])
    exact = math.floor(good * 100 / len(sets) + 0.5) if sets else 0
    asked = bet['asked']
    if asked:
        got = _answer(reps, asked)
        outcome = 'yes' if got['ver'] == latest['ver'] else 'no'
        value = f"x = {got['val']}" if got['val'] is not None else 'no value for x'
        text = f"{'Yes' if outcome == 'yes' else 'No'}. The read asked {_names(asked)} and got {value}."
        if len(sets) == 1:
            only = sets[0]
            text += (f" {_names(only)} {'was' if len(only) == 1 else 'were'} the only "
                     f"{_plural(len(only), 'replica')} it could ask, so the exact chance was {exact}%.")
        else:
            pool = 'replicas it could ask' if table['R'] == 1 else 'possible read sets'
            text += (f" {good} of the {len(sets)} {pool} {'returns' if good == 1 else 'return'} "
                     f"x = {latest['val']}, so the exact chance was {exact}%.")
    else:
        outcome = 'failed'
        reachable = ('No replicas are reachable' if not up else
                     f"Only {len(up)} {_plural(len(up), 'replica')} {'is' if len(up) == 1 else 'are'} reachable")
        text = f"No. {reachable} and R = {table['R']}, so the read fails. The exact chance was 0%."
    yes = outcome == 'yes'
    pts = points(bet['pct'], yes)
    what = {'yes': 'returned the last successful write', 'no': 'did not return the last successful write',
            'failed': 'failed'}[outcome]
    true_pct = good * 100 / len(sets) if sets else 0
    return {
        'step': step, 'pct': bet['pct'], 'asked': list(asked), 'outcome': outcome, 'yes': yes,
        'exact': exact, 'calibrated': abs(bet['pct'] - true_pct) <= CALIBRATED_WITHIN,
        'points': pts, 'text': text,
        'log': f"Read: {what}. You bet {bet['pct']}% and scored {_signed(pts)}.",
    }


def _play(table, upto, bets):
    """Replays a table's first `upto` events. `bets` maps a read's step index
    to the bet placed on it; a read without one is waiting for a bet."""
    reps = {i: {'val': None, 'ver': 0, 'st': 'up'} for i in replica_ids(table)}
    ver, latest = 0, None
    say, log, reads, pending = intro(table), [], [], False
    for i, st in enumerate(table['steps'][:upto]):
        if st['t'] == 'write':
            ver += 1
            for r in st['reach']:
                reps[r].update(val=st['val'], ver=ver)
            acks = len(st['reach'])
            counted = f"{acks} {_plural(acks, 'ack')}, W = {table['W']}"
            if acks >= table['W']:
                latest = {'val': st['val'], 'ver': ver}
                say = f"{st['say']} Acknowledged: {counted}."
            else:
                say = (f"{st['say']} Failed: {counted}. The client is told the write failed, but "
                       f"{_names(st['reach'])} keep{'s' if acks == 1 else ''} x = {st['val']}. "
                       "Nothing rolls it back.")
            log.append(say)
        elif st['t'] == 'status':
            for r, state in st['set'].items():
                reps[r]['st'] = state
            say = st['say']
            log.append(say)
        elif st['t'] == 'sync':
            reps[st['to']].update(val=reps[st['from']]['val'], ver=reps[st['from']]['ver'])
            say = st['say']
            log.append(say)
        else:
            say = (f"A client reads x, asking {table['R']} of the reachable replicas and keeping "
                   "the value with the highest version.")
            if i in bets:
                read = _resolve(table, reps, latest, i, bets[i])
                reads.append(read)
                log.append(read['log'])
            else:
                pending = True
    return {'reps': reps, 'latest': latest, 'say': say, 'log': log, 'reads': reads, 'pending': pending}


def new_run():
    return {'table': 0, 'step': 0, 'bets': [], 'done': False}


def run_fits(tables, run):
    """False if the tables changed under a saved run (say, a reseed), so it can't be replayed."""
    try:
        return 0 <= run['table'] < len(tables) and 0 <= run['step'] <= len(tables[run['table']]['steps'])
    except (KeyError, TypeError):
        return False


def _bets(run, t):
    return {b['step']: b for b in run['bets'] if b['table'] == t}


def _state(tables, run):
    return _play(tables[run['table']], run['step'], _bets(run, run['table']))


def _table_over(tables, run, state):
    return run['step'] >= len(tables[run['table']]['steps']) and not state['pending']


def _settle(tables, run):
    """Closes the run once the last table's last event has played out."""
    state = _state(tables, run)
    if run['table'] == len(tables) - 1 and _table_over(tables, run, state):
        run['done'] = True
    return state


def all_reads(tables, run):
    """Every read resolved so far, oldest first, each tagged with its table's index."""
    reads = []
    for t in range(run['table'] + 1):
        upto = run['step'] if t == run['table'] else len(tables[t]['steps'])
        reads += [dict(read, table=t) for read in _play(tables[t], upto, _bets(run, t))['reads']]
    return reads


def advance(tables, run):
    """Plays the next event, or opens the next table once this one is over.
    Returns None if the run is over or a read is waiting for a bet."""
    if run['done']:
        return None
    state = _state(tables, run)
    if state['pending']:
        return None
    if _table_over(tables, run, state):
        if run['table'] == len(tables) - 1:
            return None
        run['table'] += 1
        run['step'] = 0
    else:
        run['step'] += 1
    _settle(tables, run)
    return {'verdict': 'next'}


def place_bet(tables, run, pct, rng=random):
    """Locks in a bet of `pct`% on the read that's waiting, then draws which
    replicas it asks. Returns None if no read is waiting or the bet is out
    of range."""
    if run['done'] or isinstance(pct, bool) or not isinstance(pct, int) or not MIN_BET <= pct <= MAX_BET:
        return None
    state = _state(tables, run)
    if not state['pending']:
        return None
    _, sets = _read_sets(tables[run['table']], state['reps'])
    asked = list(rng.choice(sets)) if sets else []
    # Moves stop at a read until it's bet on, so the waiting read is always the last event played.
    run['bets'].append({'table': run['table'], 'step': run['step'] - 1, 'pct': pct, 'asked': asked})
    read = _settle(tables, run)['reads'][-1]
    return {'verdict': read['outcome'], 'points': read['points']}


def snapshot(tables, run):
    """The public view of a run: the score, the current table and its
    replicas, the ops log, and the read waiting for a bet, if any. It never
    holds the odds of a read that hasn't been bet on, or anything still to come."""
    table = tables[run['table']]
    state = _state(tables, run)
    over = _table_over(tables, run, state)
    last = state['reads'][-1] if state['reads'] and state['reads'][-1]['step'] == run['step'] - 1 else None
    latest = state['latest']
    return {
        'score': sum(r['points'] for r in all_reads(tables, run)),
        'table': run['table'] + 1, 'tables': len(tables),
        'name': table['name'], 'n': table['N'], 'w': table['W'], 'r': table['R'],
        'replicas': [dict(id=i, **state['reps'][i]) for i in replica_ids(table)],
        'latest': latest['val'] if latest else None,
        'say': table['outro'] if over else state['say'],
        'log': state['log'],
        'question': (f"Will this read return x = {latest['val']}, the last successful write?"
                     if state['pending'] else None),
        'feedback': {'points': last['points'], 'text': last['text']} if last else None,
        'asked': last['asked'] if last else [],
        'table_over': over,
        'done': run['done'],
    }


def validate_tables(tables):
    """Problems with a script of tables, as readable strings; empty if it plays."""
    if not isinstance(tables, list) or not tables:
        return ['There must be at least one table.']
    problems = []
    for t, table in enumerate(tables):
        where = f"table {t + 1}"
        if not all(isinstance(table.get(k), str) and table.get(k) for k in ('name', 'outro')):
            problems.append(f"{where}: needs a name and an outro.")
        n, w, r = table.get('N'), table.get('W'), table.get('R')
        if not (isinstance(n, int) and 1 <= n <= 26 and isinstance(w, int) and isinstance(r, int)
                and 1 <= w <= n and 1 <= r <= n):
            problems.append(f"{where}: needs 1 <= W, R <= N <= 26.")
            continue
        ids = set(replica_ids(table))
        steps = table.get('steps') or []
        acked = False
        for i, st in enumerate(steps):
            at = f"{where} step {i + 1}"
            kind = st.get('t')
            if kind != 'read' and not st.get('say'):
                problems.append(f"{at}: needs `say`.")
            if kind == 'write':
                reach = st.get('reach') or []
                if 'val' not in st or not reach or len(set(reach)) != len(reach) or not set(reach) <= ids:
                    problems.append(f"{at}: a write needs a value and distinct replicas to reach.")
                acked = acked or len(reach) >= w
            elif kind == 'status':
                change = st.get('set') or {}
                if not change or not set(change) <= ids or not set(change.values()) <= set(STATES):
                    problems.append(f"{at}: a status change maps replicas to {', '.join(STATES)}.")
            elif kind == 'sync':
                if st.get('from') not in ids or st.get('to') not in ids or st.get('from') == st.get('to'):
                    problems.append(f"{at}: a sync copies between two different replicas.")
            elif kind == 'read':
                if not acked:
                    problems.append(f"{at}: a read needs a successful write before it.")
            else:
                problems.append(f"{at}: unknown step type {kind!r}.")
        if not any(st.get('t') == 'read' for st in steps):
            problems.append(f"{where}: needs at least one read to bet on.")
    return problems
