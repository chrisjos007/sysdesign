"""Bit Budget: a time-ordered ID packs a millisecond timestamp and a few
counting fields (region, worker, a per-millisecond counter) into one integer.
The learner splits a fixed number of bits between the fields to meet a spec,
or calls the spec impossible, then answers questions on what a clock can do
to IDs like these.

The arithmetic is exact and public: the page gets every spec and works out
what a split gives as the steppers move. Whether a spec can be met at all is
never sent; the server works it out here when the learner calls it. A field
with b bits holds 2**b values. A timestamp with b bits counts 2**b
milliseconds from 00:00 UTC on 1 January of its epoch year (Unix time has no
leap seconds), and meets "no overflow before Y" when those reach 1 January Y.

A run holds only facts: the stage in play and every move (a check with its
split and epoch, a call that the spec can't be met, or an answer). The
score, feedback and scene are rebuilt from those, so a reload changes nothing.

BitBudgetChallenge.stages is a list of stages, each one of

    {'t': 'build', 'title': ..., 'text': ..., 'width': 64, 'signed': True,
     'epochs': [[1970, 'Unix, 1970'], [2026, 'Launch, 2026']], 'epoch': 1970,
     'fields': [{'key': 'ts', 'name': 'Timestamp', 'until': 2090, 'start': 40},
                {'key': 'region', 'name': 'Region', 'need': 6, 'unit': 'regions', 'start': 4}, ...],
     'done': ..., 'why': ...}
    {'t': 'clock', 'title': ..., 'text': ...,
     'questions': [{'lead': ..., 'log': [{'time': ..., 'text': ..., 'alert': False}],
                    'ask': ..., 'options': [...], 'answer': 0, 'after': ...}]}

A build stage spends `width` bits, less one if `signed` (the sign bit stays 0
so IDs are positive). The first field is the timestamp, which sits in the top
bits; `start` is the split the page opens with. One epoch means the spec fixes
it. `done` closes a spec that can be met, `why` one that can't. A clock
stage's `after` narrates each answer and should open with the right one.
"""
import datetime

BUILD_POINTS = 100
FAILED_CHECK = 25
CLOCK_RIGHT = 50
CLOCK_WRONG = 25

MS_PER_DAY = 86_400_000
MAX_WIDTH = 64
# The page colours fields with --srv-1 to --srv-5.
MAX_FIELDS = 5

KINDS = ('build', 'clock')


def min_bits(need):
    """The fewest bits whose 2**bits values cover `need`."""
    return max(0, need - 1).bit_length()


def span_ms(epoch, until):
    """Milliseconds from 1 January `epoch` to 1 January `until`, UTC."""
    return (datetime.date(until, 1, 1) - datetime.date(epoch, 1, 1)).days * MS_PER_DAY


def ts_bits(epoch, until):
    """The fewest timestamp bits that count from `epoch` into `until`."""
    return max(1, (span_ms(epoch, until) - 1).bit_length())


def runs_out(epoch, bits):
    """The year a `bits`-bit millisecond timestamp counting from `epoch`
    overflows, or None if that's after 9999."""
    try:
        return (datetime.datetime(epoch, 1, 1) + datetime.timedelta(milliseconds=2 ** bits)).year
    except OverflowError:
        return None


def budget(stage):
    return stage['width'] - (1 if stage['signed'] else 0)


def epochs(stage):
    return [year for year, _ in stage['epochs']]


def passes(field, bits, epoch):
    if 'until' in field:
        return 2 ** bits >= span_ms(epoch, field['until'])
    return 2 ** bits >= field['need']


def _counted_bits(stage):
    """The fewest bits the fields after the timestamp need between them."""
    return sum(min_bits(f['need']) for f in stage['fields'][1:])


def cheapest(stage):
    """(bits, epoch): the fewest bits that meet every need, and the earliest
    epoch that gets them."""
    until = stage['fields'][0]['until']
    epoch = min(epochs(stage), key=lambda e: (ts_bits(e, until), e))
    return _counted_bits(stage) + ts_bits(epoch, until), epoch


def possible(stage):
    return cheapest(stage)[0] <= budget(stage)


def _series(names):
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1]


def _lower(name):
    return name[:1].lower() + name[1:]


def _shortfall(field, bits, epoch):
    if 'until' in field:
        year = runs_out(epoch, bits)
        return f"the {_lower(field['name'])} runs out in {year}, before {field['until']}"
    return f"{_lower(field['name'])} gives {2 ** bits:,} {field['unit']}, short of {field['need']:,}"


def _proof(stage):
    """Why no split meets the stage, in numbers."""
    ts, *rest = stage['fields']
    counted = [f for f in rest if min_bits(f['need'])]
    parts = [min_bits(f['need']) for f in counted]
    total, epoch = cheapest(stage)
    t = ts_bits(epoch, ts['until'])
    lines = []
    if counted:
        sums = ' + '.join(map(str, parts)) + f' = {sum(parts)}' if len(parts) > 1 else str(parts[0])
        names = _series([_lower(f['name']) for f in counted])
        verb = 'need' if len(counted) > 1 else 'needs'
        lines.append(f"{names[:1].upper()}{names[1:]} {verb} at least {sums} bits.")
    fewer = f', and {t - 1} bits run out in {runs_out(epoch, t - 1)}' if t > 1 else ''
    since = 'from' if len(stage['epochs']) == 1 else 'even from'
    lines.append(f"The timestamp needs {t} bits to reach {ts['until']} {since} {epoch}{fewer}.")
    lines.append(f"That's {total} bits against a budget of {budget(stage)}.")
    return ' '.join(lines)


def _check_result(stage, move):
    split, epoch = move['bits'], move['epoch']
    marks = [passes(f, b, epoch) for f, b in zip(stage['fields'], split)]
    if all(marks):
        return {'ok': True, 'points': BUILD_POINTS, 'marks': marks,
                'text': f"Spec met: +{BUILD_POINTS}. {stage['done']}"}
    short = [_shortfall(f, b, epoch) for f, b, ok in zip(stage['fields'], split, marks) if not ok]
    return {'ok': False, 'points': -FAILED_CHECK, 'marks': marks, 'text': f"Not yet: {'; '.join(short)}."}


def _claim_result(stage):
    if not possible(stage):
        return {'ok': True, 'points': BUILD_POINTS, 'marks': None,
                'text': f"Right, it can't be done: +{BUILD_POINTS}. {_proof(stage)} {stage['why']}"}
    until = stage['fields'][0]['until']
    # Nudge towards the epoch when some epoch on offer can't meet the spec.
    epoch_matters = any(_counted_bits(stage) + ts_bits(e, until) > budget(stage) for e in epochs(stage))
    hint = ', and look at the epoch.' if epoch_matters else '.'
    return {'ok': False, 'points': -FAILED_CHECK, 'marks': None,
            'text': f'It can be done. Keep adjusting the fields{hint}'}


def _answer_result(stage, q, choice):
    question = stage['questions'][q]
    right = choice == question['answer']
    lead = 'Right.' if right else 'Not quite.'
    return {'right': right, 'points': CLOCK_RIGHT if right else -CLOCK_WRONG, 'text': f"{lead} {question['after']}"}


def _stage_moves(run, i):
    return [m for m in run['moves'] if m['stage'] == i]


def _stage_state(stages, run, i):
    stage = stages[i]
    moves = _stage_moves(run, i)
    if stage['t'] == 'build':
        results = [_check_result(stage, m) if m['kind'] == 'check' else _claim_result(stage) for m in moves]
        # A cleared stage takes no more moves, so a clearing one is always the last.
        cleared = bool(results) and results[-1]['ok']
    else:
        results = [_answer_result(stage, q, m['choice']) for q, m in enumerate(moves)]
        cleared = len(results) == len(stage['questions'])
    return {'moves': moves, 'results': results, 'cleared': cleared}


def score(stages, run):
    return sum(r['points'] for i in range(run['stage'] + 1) for r in _stage_state(stages, run, i)['results'])


def new_run():
    return {'stage': 0, 'moves': [], 'done': False}


def _split_fits(stage, split, epoch):
    return (isinstance(split, list) and len(split) == len(stage['fields'])
            and all(isinstance(b, int) and not isinstance(b, bool) for b in split)
            and split[0] >= 1 and all(b >= 0 for b in split) and sum(split) <= budget(stage)
            and isinstance(epoch, int) and not isinstance(epoch, bool) and epoch in epochs(stage))


def run_fits(stages, run):
    """False if the stages changed under a saved run (say, a reseed), so it can't be replayed."""
    try:
        if not 0 <= run['stage'] < len(stages) or not isinstance(run['moves'], list):
            return False
        for m in run['moves']:
            if not 0 <= m['stage'] <= run['stage']:
                return False
            stage = stages[m['stage']]
            if m['kind'] == 'check':
                if stage['t'] != 'build' or not _split_fits(stage, m['bits'], m['epoch']):
                    return False
            elif m['kind'] == 'claim':
                if stage['t'] != 'build':
                    return False
            elif m['kind'] == 'answer':
                if stage['t'] != 'clock':
                    return False
            else:
                return False
        for i, stage in enumerate(stages):
            if stage['t'] == 'clock':
                picks = _stage_moves(run, i)
                if len(picks) > len(stage['questions']) or not all(
                        isinstance(m['choice'], int) and 0 <= m['choice'] < len(q['options'])
                        for m, q in zip(picks, stage['questions'])):
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


def _record(stages, run, move):
    run['moves'].append(move)
    result = _stage_state(stages, run, run['stage'])['results'][-1]
    _settle(stages, run)
    return result


def check(stages, run, split, epoch):
    """Checks a split (bits per field, timestamp first) from `epoch` on the
    build stage in play. Returns None if the move doesn't fit."""
    if _open_stage(stages, run, 'build') is None or not _split_fits(stages[run['stage']], split, epoch):
        return None
    result = _record(stages, run, {'stage': run['stage'], 'kind': 'check', 'bits': list(split), 'epoch': epoch})
    return {'verdict': 'met' if result['ok'] else 'short', 'points': result['points']}


def claim(stages, run):
    """Calls the build stage in play impossible. Returns None if there isn't one."""
    if _open_stage(stages, run, 'build') is None:
        return None
    result = _record(stages, run, {'stage': run['stage'], 'kind': 'claim'})
    return {'verdict': 'right' if result['ok'] else 'wrong', 'points': result['points']}


def answer(stages, run, choice):
    """Answers the waiting clock question with option `choice`. Returns None
    if no question is waiting or there's no such option."""
    state = _open_stage(stages, run, 'clock')
    if state is None or isinstance(choice, bool) or not isinstance(choice, int):
        return None
    question = stages[run['stage']]['questions'][len(state['results'])]
    if not 0 <= choice < len(question['options']):
        return None
    result = _record(stages, run, {'stage': run['stage'], 'kind': 'answer', 'choice': choice})
    return {'verdict': 'right' if result['right'] else 'wrong', 'points': result['points']}


def advance(stages, run):
    """Opens the next stage once this one is cleared. Returns None otherwise."""
    if run['done'] or run['stage'] >= len(stages) - 1:
        return None
    if not _stage_state(stages, run, run['stage'])['cleared']:
        return None
    run['stage'] += 1
    return {'verdict': 'next'}


def _public_question(question, n, of):
    return {'n': n, 'of': of, 'lead': question['lead'], 'log': question['log'],
            'ask': question['ask'], 'options': question['options']}


def snapshot(stages, run):
    """The public view of a run: the score, the stage in play and the last
    move's feedback. It never says whether a spec can be met, or the answer
    to a question that's still waiting."""
    i = run['stage']
    stage = stages[i]
    state = _stage_state(stages, run, i)
    results = state['results']
    snap = {
        'score': score(stages, run),
        'stage': i + 1, 'stages': len(stages), 'kind': stage['t'], 'title': stage['title'], 'text': stage['text'],
        'feedback': {'points': results[-1]['points'], 'text': results[-1]['text']} if results else None,
        'cleared': state['cleared'], 'last': i == len(stages) - 1, 'done': run['done'],
    }
    if stage['t'] == 'build':
        checks = [m for m in state['moves'] if m['kind'] == 'check']
        split, epoch = ((checks[-1]['bits'], checks[-1]['epoch']) if checks
                        else ([f['start'] for f in stage['fields']], stage['epoch']))
        last = results[-1] if results and state['moves'][-1]['kind'] == 'check' else None
        snap.update(
            width=stage['width'], signed=stage['signed'], budget=budget(stage),
            epochs=[{'year': year, 'label': label} for year, label in stage['epochs']],
            fields=[{k: f[k] for k in ('key', 'name', 'unit', 'need', 'until') if k in f} for f in stage['fields']],
            bits=split, epoch=epoch,
            checked={'bits': split, 'epoch': epoch, 'marks': last['marks']} if last else None,
        )
    else:
        questions = stage['questions']
        done_q = len(results)
        snap['question'] = None if state['cleared'] else _public_question(questions[done_q], done_q + 1, len(questions))
        snap['answered'] = None
        if results:
            q = questions[done_q - 1]
            snap['answered'] = dict(_public_question(q, done_q, len(questions)),
                                    choice=state['moves'][-1]['choice'], answer=q['answer'])
    return snap


def summary(stages, run):
    """One line per stage played, for the verdict and the attempt's detail."""
    lines = []
    for i in range(run['stage'] + 1):
        stage = stages[i]
        state = _stage_state(stages, run, i)
        results, moves = state['results'], state['moves']
        line = {'title': stage['title'], 'kind': stage['t'], 'points': sum(r['points'] for r in results)}
        if stage['t'] == 'build':
            line.update(
                failed=sum(1 for m, r in zip(moves, results) if m['kind'] == 'check' and not r['ok']),
                wrong_calls=sum(1 for m, r in zip(moves, results) if m['kind'] == 'claim' and not r['ok']),
                cleared=state['cleared'],
                how=(moves[-1]['kind'] if state['cleared'] else None),
                bits=moves[-1]['bits'] if state['cleared'] and moves[-1]['kind'] == 'check' else None,
                epoch=moves[-1]['epoch'] if state['cleared'] and moves[-1]['kind'] == 'check' else None,
            )
        else:
            line.update(right=sum(1 for r in results if r['right']), questions=len(stage['questions']))
        lines.append(line)
    return lines


def _whole(value, low=None):
    return isinstance(value, int) and not isinstance(value, bool) and (low is None or value >= low)


def validate_stages(stages):
    """Problems with a list of stages, as readable strings; empty if it plays."""
    if not isinstance(stages, list) or not stages:
        return ['There must be at least one stage.']
    problems = []
    for i, stage in enumerate(stages):
        where = f'stage {i + 1}'
        if not all(isinstance(stage.get(key), str) and stage.get(key) for key in ('title', 'text')):
            problems.append(f'{where}: needs a title and a text.')
        kind = stage.get('t')
        if kind == 'build':
            problems += _build_problems(stage, where)
        elif kind == 'clock':
            questions = stage.get('questions') or []
            if not questions:
                problems.append(f'{where}: needs at least one question.')
            for q, question in enumerate(questions):
                options = question.get('options') or []
                log = question.get('log')
                if (not all(isinstance(question.get(k), str) and question.get(k) for k in ('lead', 'ask', 'after'))
                        or not isinstance(log, list) or not all(isinstance(line, dict) and line.get('text') for line in log)
                        or len(options) < 2 or not all(isinstance(o, str) and o for o in options)
                        or not _whole(question.get('answer'), 0) or question['answer'] >= len(options)):
                    problems.append(f'{where} question {q + 1}: needs lead, log lines with text, ask, after, '
                                    'two or more options and the index of the right one.')
        else:
            problems.append(f'{where}: unknown stage type {kind!r}.')
    return problems


def _build_problems(stage, where):
    width = stage.get('width')
    if not _whole(width, 2) or width > MAX_WIDTH or not isinstance(stage.get('signed'), bool):
        return [f'{where}: needs a width from 2 to {MAX_WIDTH} bits and `signed`.']
    choices = stage.get('epochs') or []
    if (not all(isinstance(c, (list, tuple)) and len(c) == 2 and _whole(c[0], 1970) and isinstance(c[1], str)
                for c in choices) or not choices or stage.get('epoch') not in [c[0] for c in choices]):
        return [f'{where}: needs epochs as [year, label] pairs from 1970 on, and a starting epoch among them.']
    fields = stage.get('fields') or []
    if not 2 <= len(fields) <= MAX_FIELDS or len({f.get('key') for f in fields}) != len(fields):
        return [f'{where}: needs 2 to {MAX_FIELDS} fields with distinct keys.']
    ts, *rest = fields
    if (not ts.get('name') or 'need' in ts or not _whole(ts.get('until'))
            or ts['until'] <= max(c[0] for c in choices) or ts['until'] > 9999):
        return [f'{where}: the first field must be the timestamp, with an `until` year after every epoch.']
    if not all(f.get('name') and f.get('unit') and 'until' not in f and _whole(f.get('need'), 1) for f in rest):
        return [f'{where}: every field after the timestamp needs a name, a unit and a `need` of 1 or more.']
    start = [f.get('start') for f in fields]
    if not _split_fits(stage, start, stage['epoch']):
        return [f'{where}: the starting split must give the timestamp at least 1 bit and fit in {budget(stage)} bits.']
    if possible(stage) and not (isinstance(stage.get('done'), str) and stage['done']):
        return [f'{where}: this spec can be met, so it needs `done`.']
    if not possible(stage) and not (isinstance(stage.get('why'), str) and stage['why']):
        return [f"{where}: this spec can't be met, so it needs `why`."]
    return []
