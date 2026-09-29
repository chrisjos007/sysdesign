const test = require('node:test');
const assert = require('node:assert/strict');
const {estimate, fleet} = require('../static/learn/capacity_model.js');

test('worked example preserves decimal units and converts bytes to bits', () => {
    const r = estimate(100000, 20, 30);
    assert.equal(r.dailyReads, 2000000);
    assert.ok(Math.abs(r.averageRps - 23.148148148) < 1e-8);
    assert.ok(Math.abs(r.peakRps - 462.962962963) < 1e-8);
    assert.equal(r.payloadGB, 20);
    assert.ok(Math.abs(r.peakMbps - 37.037037037) < 1e-8);
    assert.equal(r.eventMB, 250);
    assert.equal(r.storageGB, 7.5);
});
test('practice changes peak and retention independently of daily volume', () => {
    const r = estimate(100000, 40, 365);
    assert.equal(r.storageGB, 91.25);
    assert.ok(Math.abs(r.peakRps - 925.925925926) < 1e-8);
    assert.equal(r.payloadGB, 20);
    assert.deepEqual(fleet(r.peakRps, 200, 1), {serving: 5, provisioned: 6});
});
test('capacity rounds up and reserves a failed server separately', () => {
    assert.deepEqual(fleet(400, 200, 0), {serving: 2, provisioned: 2});
    assert.deepEqual(fleet(400.01, 200, 1), {serving: 3, provisioned: 4});
    for (const users of [10000, 100000, 1000000]) {
        for (const peak of [1, 20, 40]) {
            const demand = estimate(users, peak, 365).peakRps;
            const count = fleet(demand, 200, 1).provisioned;
            assert.ok((count - 1) * 200 >= demand);
            assert.ok((count - 2) * 200 < demand);
        }
    }
});
test('zero activity gives zero demand; invalid assumptions are rejected', () => {
    assert.equal(estimate(0, 20, 30).storageGB, 0);
    for (const args of [[NaN, 20, 30], [-1, 20, 30], [100000, 0, 30], [100000, 20, 0]]) {
        assert.throws(() => estimate(...args), RangeError);
    }
    for (const args of [[100, 0, 1], [Infinity, 200, 1], [100, 200, -1]]) {
        assert.throws(() => fleet(...args), RangeError);
    }
});
