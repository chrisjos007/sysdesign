/* Deterministic teaching models. These examples never send network requests. */
(function (root, factory) {
    'use strict';
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.HttpContractModel = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';
    var methods = {
        get: {label: 'GET', safe: true, idempotent: true, request: 'GET /tasks/9',
            note: 'GET asks to read, not change, the task. Incidental logging is allowed; safe does not mean the server does no work.'},
        put: {label: 'PUT', safe: false, idempotent: true, request: 'PUT /tasks/9\nContent-Type: application/json\n\n{"title":"Review plan"}',
            note: 'Both requests set the same representation. This task has one editable field, title; a full-resource PUT needs a clear contract for all fields.'},
        delete: {label: 'DELETE', safe: false, idempotent: true, request: 'DELETE /tasks/9',
            note: '204 then 404 is valid here. After either request the task is absent. Idempotence concerns intended effects, not identical responses.'},
        post: {label: 'POST', safe: false, idempotent: false, request: 'POST /tasks\nContent-Type: application/json\n\n{"title":"Review plan"}',
            note: 'In this API, each unkeyed POST creates a new task. An identical body does not give POST a general idempotency guarantee.'},
        keyed: {label: 'POST + key', safe: false, idempotent: true, request: 'POST /tasks\nIdempotency-Key: task-demo-1\nContent-Type: application/json\n\n{"title":"Review plan"}',
            note: 'This API replays the saved creation result for the same key and body. That guarantee comes from the API contract, not from POST itself.'}
    };

    function newReplay(mode) {
        if (!Object.prototype.hasOwnProperty.call(methods, mode)) throw new Error('Unknown method scenario');
        return {mode: mode, attempts: 0, created: 0, exists: true, title: 'Draft plan'};
    }

    function sendAgain(state) {
        var next = Object.assign({}, state, {attempts: state.attempts + 1});
        switch (state.mode) {
        case 'get':
            next.response = '200 OK\n\n{"id":9,"title":"Draft plan"}';
            next.effect = 'Task 9 is unchanged: “Draft plan”.';
            break;
        case 'put':
            next.title = 'Review plan';
            next.response = '204 No Content';
            next.effect = 'Task 9 is “Review plan”. Repeating the replacement adds no task.';
            break;
        case 'delete':
            next.exists = false;
            next.response = state.exists ? '204 No Content' : '404 Not Found';
            next.effect = 'Task 9 is absent. No further state change on a repeat.';
            break;
        case 'post':
        case 'keyed':
            next.created = state.mode === 'keyed' ? 1 : state.created + 1;
            var id = 9 + next.created;
            next.response = '201 Created\nLocation: /tasks/' + id + '\n\n{"id":' + id + ',"title":"Review plan"}';
            next.effect = next.created + ' new task' + (next.created === 1 ? '' : 's') + ' created.';
            if (state.mode === 'keyed' && state.attempts) next.effect += ' The original result was replayed.';
            break;
        }
        return next;
    }

    function newEdit() {
        return {version: 7, title: 'Draft plan', clients: {
            a: {version: 7, draft: 'Review plan'}, b: {version: 7, draft: 'Ship plan'}
        }};
    }

    function saveEdit(state, client, draft) {
        if (!state.clients[client]) throw new Error('Unknown editor');
        var next = Object.assign({}, state, {clients: Object.assign({}, state.clients)});
        var editor = Object.assign({}, state.clients[client], {draft: draft});
        next.clients[client] = editor;
        next.request = 'PUT /tasks/9\nIf-Match: "v' + editor.version + '"\nContent-Type: application/json\n\n' + JSON.stringify({title: draft});
        if (!draft.trim() || draft.length > 80) {
            next.response = '400 Bad Request';
            next.message = 'Use a non-empty title of at most 80 characters. The task was not changed.';
        } else if (editor.version !== state.version) {
            next.response = '412 Precondition Failed';
            next.message = 'This editor has a stale ETag. The server kept its current title. Refresh, compare the titles, then decide whether to save your draft.';
        } else {
            next.title = draft;
            next.version = state.version + (draft === state.title ? 0 : 1);
            editor.version = next.version;
            next.response = '204 No Content\nETag: "v' + next.version + '"';
            next.message = 'The precondition matched. The server saved the title and returned its current ETag.';
        }
        return next;
    }

    function refreshEdit(state, client, draft) {
        if (!state.clients[client]) throw new Error('Unknown editor');
        var next = Object.assign({}, state, {clients: Object.assign({}, state.clients)});
        next.clients[client] = {version: state.version, draft: draft};
        next.request = 'GET /tasks/9';
        next.response = '200 OK\nETag: "v' + state.version + '"\n\n' + JSON.stringify({id: 9, title: state.title});
        next.message = 'Latest title and ETag loaded. Your draft is kept for comparison; refreshing does not save or merge it. Review before saving.';
        return next;
    }

    function newExport() {
        return {state: 'not submitted', observed: null,
            request: 'POST /exports\nIdempotency-Key: report-demo-1\nContent-Type: application/json\n\n{"report":"weekly-sales","format":"csv"}',
            response: 'No response yet. Submit the export to begin.',
            message: 'In this teaching API, 202 is returned only after durable acceptance.'};
    }

    function exportAction(state, action) {
        var next = Object.assign({}, state);
        if (action === 'submit') {
            if (state.state === 'not submitted') next.state = 'queued';
            next.request = newExport().request;
            next.response = '202 Accepted\nLocation: /operations/123\n\n{"operation_id":"123","status_url":"/operations/123"}';
            next.message = state.state === 'not submitted'
                ? 'Operation 123 was durably accepted. No report is promised yet. Read its status to learn the outcome.'
                : 'The same key and body return the same operation 123. This repeats acceptance, not proof of completion; read the status resource.';
        } else if (action === 'start' && state.state === 'queued') {
            next.state = 'running';
        } else if ((action === 'succeed' || action === 'fail') && state.state === 'running') {
            next.state = action === 'succeed' ? 'succeeded' : 'failed';
        } else if ((action === 'poll' || action === 'unreachable') && state.state !== 'not submitted') {
            next.request = 'GET /operations/123';
            if (action === 'unreachable') {
                next.response = 'Network timeout · no HTTP response';
                next.message = state.observed === 'succeeded' || state.observed === 'failed'
                    ? 'The status lookup timed out. The last confirmed terminal result (' + state.observed + ') remains known. This network error is not a new operation result.'
                    : 'The current outcome is unknown to the client. A failed status lookup does not mean the export failed. The last confirmed observation stays unchanged.';
            } else {
                next.observed = state.state;
                var body = {id: '123', state: state.state};
                if (state.state === 'succeeded') body.result_url = '/reports/weekly-sales.csv';
                if (state.state === 'failed') body.error = 'Report source unavailable';
                next.response = '200 OK\n\n' + JSON.stringify(body, null, 2);
                next.message = state.state === 'failed'
                    ? 'The status lookup succeeded (200); its body reports that the export failed. This is a terminal operation result.'
                    : state.state === 'succeeded' ? 'The status body confirms completion and supplies the report URL.'
                        : 'The status lookup succeeded, but the export is not finished. Queued and running are nonterminal states.';
            }
        }
        return next;
    }

    return {methods: methods, newReplay: newReplay, sendAgain: sendAgain,
        newEdit: newEdit, saveEdit: saveEdit, refreshEdit: refreshEdit,
        newExport: newExport, exportAction: exportAction};
}));
