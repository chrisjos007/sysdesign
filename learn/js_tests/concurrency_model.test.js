const {test} = require('node:test');
const assert = require('node:assert/strict');
const {create, step} = require('../static/learn/concurrency_model.js');
const run = (mode, order) => order.reduce(step, create(mode));

test('alternating workers lose an increment without a common boundary', () => {
    for (const mode of ['unsafe', 'separate-locks']) {
        const state = run(mode, [0, 1, 0, 1, 0, 1]);
        assert.equal(state.balance, 11);
        assert.ok(state.workers.every(w => w.phase === 3));
        assert.equal(run(mode, [0, 0, 0, 1, 1, 1]).balance, 12);
    }
});
test('shared lock covers read, calculate and write, then releases', () => {
    let state = run('shared-lock', [0, 1, 0, 1]);
    assert.equal(state.balance, 10);
    assert.equal(state.workers[1].phase, 0);
    assert.equal(state.workers[1].local, null);
    state = [0, 1, 1, 1].reduce(step, state);
    assert.equal(state.balance, 12);
    assert.equal(state.owner, null);
});
test('all possible completing schedules preserve both increments with protection', () => {
    for (const mode of ['shared-lock', 'atomic']) {
        let completed = 0;
        function explore(state) {
            if (state.workers.every(w => w.phase === 3)) {
                completed++;
                assert.equal(state.balance, 12);
                return;
            }
            for (const index of [0, 1]) {
                const next = step(state, index);
                if (next.workers[index].phase !== state.workers[index].phase) explore(next);
            }
        }
        explore(create(mode));
        assert.equal(completed, 2);
    }
});
test('all 20 unprotected schedules include safe and lost-update outcomes', () => {
    const results = [];
    function explore(state) {
        if (state.workers.every(w => w.phase === 3)) return results.push(state.balance);
        for (const index of [0, 1]) {
            if (state.workers[index].phase < 3) explore(step(state, index));
        }
    }
    explore(create());
    assert.equal(results.length, 20);
    assert.deepEqual(new Set(results), new Set([11, 12]));
});
test('finished workers cannot repeat effects; reset starts clean; steps preserve inputs', () => {
    const original = create();
    const snapshot = JSON.stringify(original);
    step(original, 0);
    assert.equal(JSON.stringify(original), snapshot);
    const done = run('atomic', [0, 1]);
    assert.deepEqual(step(done, 0), done);
    assert.equal(create('atomic').balance, 10);
    assert.equal(create().history.length, 0);
    assert.throws(() => create('unknown'), RangeError);
    assert.throws(() => step(original, 2), RangeError);
});
