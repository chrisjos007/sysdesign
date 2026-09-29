const test = require('node:test');
const assert = require('node:assert/strict');
const model = require('../static/learn/latency_model.js');

test('five-minute overload builds 6000 jobs and spare capacity drains them in five minutes', () => {
    const initial = model.newQueue();
    const burst = model.advance(initial, 120, 100, 300);
    assert.equal(burst.backlog, 6000);
    assert.equal(burst.throughput, 100);
    assert.equal(burst.arrived, 36000);
    assert.equal(burst.completed, 30000);
    assert.equal(model.drainSeconds(burst.backlog, 80, 100), 300);
    const drained = model.advance(burst, 80, 100, 300);
    assert.equal(drained.backlog, 0);
    assert.equal(drained.seconds, 600);
    assert.equal(initial.backlog, 0);
    assert.equal(burst.backlog, 6000);
});

test('completion is bounded by available work; an interval can include idle time', () => {
    const burst = model.advance(model.newQueue(), 120, 100, 60);
    const drained = model.advance(burst, 0, 100, 60);
    assert.equal(drained.throughput, 20);
    assert.equal(drained.backlog, 0);
    assert.equal(model.advance(model.newQueue(), 80, 100, 60).throughput, 80);
});

test('no capacity, equal rates, and sustained overload never drain existing work', () => {
    for (const [arrivals, capacity] of [[0, 0], [100, 100], [120, 100]]) {
        assert.equal(model.drainSeconds(6000, arrivals, capacity), Infinity);
    }
    assert.equal(model.drainSeconds(0, 120, 100), 0);
    assert.equal(model.advance(model.newQueue(), 120, 0, 60).backlog, 7200);
});

test('work is conserved across changing rates and never becomes negative', () => {
    let state = model.newQueue();
    for (const arrival of [200, 80, 0, 120, 50]) {
        for (const capacity of [0, 100, 200]) {
            state = model.advance(state, arrival, capacity, 300);
            assert.equal(state.arrived - state.completed, state.backlog);
            assert.ok(state.backlog >= 0);
            assert.ok(state.throughput <= capacity);
        }
    }
});

test('Little’s Law converts milliseconds and uses mean latency', () => {
    assert.equal(model.concurrency(200, 150), 30);
    assert.equal(model.concurrency(200, 600), 120);
    assert.equal(model.concurrency(50, 200), 10);
});

test('nearest-rank percentiles reveal the exact 1% boundary', () => {
    assert.deepEqual(model.tail(10), {fastCount: 990, slowCount: 10, mean: 39.8, p50: 20, p99: 20, p999: 2000});
    assert.equal(model.tail(11).p99, 2000);
    assert.equal(model.tail(20).mean, 59.6);
    assert.equal(model.tail(20).p50, 20);
    assert.equal(model.tail(0).p999, 20);
    assert.equal(model.tail(1000).p50, 2000);
});

test('invalid measurements cannot silently produce plausible teaching results', () => {
    for (const value of [-1, NaN, Infinity]) {
        assert.throws(() => model.concurrency(value, 150), RangeError);
        assert.throws(() => model.advance(model.newQueue(), value, 100, 60), RangeError);
    }
    for (const count of [-1, 1001, 1.5]) assert.throws(() => model.tail(count), RangeError);
});
