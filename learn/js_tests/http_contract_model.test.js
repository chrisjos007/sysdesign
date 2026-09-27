const test = require('node:test');
const assert = require('node:assert/strict');
const model = require('../static/learn/http_contract_model.js');

test('GET leaves the task unchanged; repeated PUT sets the same representation', () => {
    for (const mode of ['get', 'put']) {
        const initial = model.newReplay(mode);
        const first = model.sendAgain(initial);
        const second = model.sendAgain(first);
        assert.equal(initial.title, 'Draft plan');
        assert.equal(second.title, first.title);
        assert.equal(second.created, 0);
        assert.equal(second.exists, true);
        assert.equal(second.attempts, 2);
    }
    assert.equal(model.methods.get.safe, true);
    assert.equal(model.methods.put.safe, false);
});

test('DELETE returns 204 then 404 without another state change', () => {
    const first = model.sendAgain(model.newReplay('delete'));
    const second = model.sendAgain(first);
    assert.equal(first.response, '204 No Content');
    assert.equal(second.response, '404 Not Found');
    assert.equal(first.exists, false);
    assert.equal(second.exists, false);
    assert.equal(model.newReplay('delete').exists, true);
});

test('unkeyed POST creates duplicates; a repeated keyed POST replays one result', () => {
    for (const mode of ['post', 'keyed']) {
        const first = model.sendAgain(model.newReplay(mode));
        let result = first;
        for (let i = 1; i < 4; i++) result = model.sendAgain(result);
        assert.equal(result.created, mode === 'keyed' ? 1 : 4);
        if (mode === 'keyed') assert.equal(result.response, first.response);
        else assert.notEqual(result.response, first.response);
    }
    assert.equal(model.methods.post.idempotent, false);
});

test('either editor can win; a stale update never overwrites the saved title', () => {
    for (const [first, second] of [['a', 'b'], ['b', 'a']]) {
        const initial = model.newEdit();
        const saved = model.saveEdit(initial, first, 'First edit');
        const rejected = model.saveEdit(saved, second, 'Second edit');
        assert.equal(initial.version, 7);
        assert.equal(initial.clients[first].version, 7);
        assert.equal(saved.version, 8);
        assert.equal(rejected.response, '412 Precondition Failed');
        assert.equal(rejected.title, 'First edit');
        assert.equal(rejected.version, 8);
        assert.match(rejected.request, /If-Match: "v7"/);
    }
});

test('refresh keeps the draft but only a new explicit save changes the server', () => {
    const saved = model.saveEdit(model.newEdit(), 'a', 'First edit');
    const refreshed = model.refreshEdit(saved, 'b', 'My revised draft');
    assert.equal(refreshed.title, 'First edit');
    assert.equal(refreshed.clients.b.draft, 'My revised draft');
    assert.equal(refreshed.clients.b.version, 8);
    const resolved = model.saveEdit(refreshed, 'b', refreshed.clients.b.draft);
    assert.equal(resolved.title, 'My revised draft');
    assert.equal(resolved.version, 9);
    assert.match(resolved.response, /^204 No Content/);
    assert.equal(model.saveEdit(resolved, 'b', resolved.title).version, 9);
});

test('invalid titles never mutate the task', () => {
    for (const title of ['', '   ', 'x'.repeat(81)]) {
        const rejected = model.saveEdit(model.newEdit(), 'a', title);
        assert.equal(rejected.response, '400 Bad Request');
        assert.equal(rejected.version, 7);
        assert.equal(rejected.title, 'Draft plan');
    }
});

test('202 and repeated acceptance reference one operation without promising completion', () => {
    const accepted = model.exportAction(model.newExport(), 'submit');
    const replay = model.exportAction(accepted, 'submit');
    assert.equal(accepted.state, 'queued');
    assert.equal(accepted.observed, null);
    assert.equal(accepted.response, replay.response);
    assert.match(replay.response, /202 Accepted\nLocation: \/operations\/123/);
    assert.doesNotMatch(replay.response, /result_url/);
});

test('worker changes require a fresh client observation; a lost lookup is not failure', () => {
    let state = model.exportAction(model.newExport(), 'submit');
    state = model.exportAction(state, 'poll');
    assert.equal(state.observed, 'queued');
    state = model.exportAction(state, 'start');
    state = model.exportAction(state, 'succeed');
    assert.equal(state.observed, 'queued');
    const unavailable = model.exportAction(state, 'unreachable');
    assert.equal(unavailable.state, 'succeeded');
    assert.equal(unavailable.observed, 'queued');
    assert.match(unavailable.response, /no HTTP response/);
    const observed = model.exportAction(unavailable, 'poll');
    assert.equal(observed.observed, 'succeeded');
    assert.match(observed.response, /result_url/);
});

test('failure is a terminal operation result inside a successful status lookup', () => {
    let state = model.exportAction(model.newExport(), 'submit');
    state = model.exportAction(state, 'start');
    state = model.exportAction(state, 'fail');
    assert.equal(model.exportAction(state, 'succeed').state, 'failed');
    assert.equal(model.exportAction(state, 'submit').state, 'failed');
    const result = model.exportAction(state, 'poll');
    assert.match(result.response, /^200 OK/);
    assert.match(result.response, /"state": "failed"/);
    assert.equal(result.observed, 'failed');
    const unavailable = model.exportAction(result, 'unreachable');
    assert.equal(unavailable.observed, 'failed');
    assert.match(unavailable.message, /terminal result \(failed\) remains known/);
    assert.equal(model.newExport().state, 'not submitted');
});
