const {test} = require('node:test');
const assert = require('node:assert/strict');
const {orders, compare, planRows, queryCount} = require('../static/learn/indexes_model.js');

test('every path returns the same correct top orders, including timestamp ties', () => {
    for (const workload of ['sparse', 'busy']) {
        const expected = orders(workload).filter(row => row.tenant === 7 && row.status === 'open')
            .sort((a, b) => b.createdAt - a.createdAt || b.id - a.id).slice(0, 20).map(row => row.id);
        for (const path of ['scan', 'tenant', 'composite']) {
            assert.deepEqual(compare(workload, path).ids, expected);
        }
    }
    assert.deepEqual(compare('sparse', 'composite').ids, [97, 87, 77, 67, 57, 47, 37, 27, 17, 7]);
    assert.deepEqual(compare('busy', 'composite').ids.slice(0, 3), [897, 887, 877]);
});
test('limit can stop the ordered range but cannot skip unsorted input', () => {
    for (const workload of ['sparse', 'busy']) {
        const scan = compare(workload, 'scan');
        const tenant = compare(workload, 'tenant');
        const composite = compare(workload, 'composite');
        const matches = workload === 'sparse' ? 10 : 90;
        assert.equal(scan.examined, 1000);
        assert.equal(tenant.examined, 100);
        assert.equal(scan.sortInput, matches);
        assert.equal(tenant.sortInput, matches);
        assert.equal(composite.sortInput, 0);
        assert.equal(composite.examined, Math.min(matches, 20));
        assert.equal(composite.returned, Math.min(matches, 20));
    }
});
test('plan output multiplies actual average rows by loops, independent of estimate', () => {
    assert.deepEqual(planRows(1, 10, 50), {factor: 10, total: 500});
    assert.deepEqual(planRows(10, 10, 50), {factor: 1, total: 500});
    assert.deepEqual(planRows(10, 0, 50), {factor: 0, total: 0});
});
test('N+1 grows with projects while join and bounded batch counts stay fixed', () => {
    for (const projects of [1, 10, 50, 100]) {
        assert.equal(queryCount(projects, 'individual'), projects + 1);
        assert.equal(queryCount(projects, 'join'), 1);
        assert.equal(queryCount(projects, 'batch'), 2);
    }
});
test('unknown scenarios and invalid numeric inputs are rejected', () => {
    assert.throws(() => compare('unknown', 'scan'), RangeError);
    assert.throws(() => compare('sparse', 'unknown'), RangeError);
    for (const value of [0, -1, 1.5, NaN, Infinity, '50', 101]) {
        assert.throws(() => queryCount(value, 'individual'), RangeError);
    }
    assert.throws(() => queryCount(50, 'unknown'), RangeError);
    assert.throws(() => planRows(0, 10, 50), RangeError);
    assert.throws(() => planRows(1, -10, 50), RangeError);
    assert.throws(() => planRows(1, 10, 0), RangeError);
});
