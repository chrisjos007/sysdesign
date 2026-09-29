(function () {
    'use strict';
    var root = document.getElementById('http-lesson');
    var model = window.HttpContractModel;
    if (!root || !model) return;
    var replay = model.newReplay('delete');
    var editing = model.newEdit();
    var exporting = model.newExport();
    function el(id) { return document.getElementById(id); }
    function text(id, value) { el(id).textContent = value; }

    function renderReplay() {
        var method = model.methods[replay.mode];
        text('http-safe', method.safe ? 'Yes' : 'No');
        text('http-idempotent', replay.mode === 'keyed' ? 'Yes, by this API contract' : method.idempotent ? 'Yes' : 'Not guaranteed');
        text('http-replay-request', method.request);
        text('http-method-note', method.note);
        text('http-attempts', replay.attempts ? 'Requests sent: ' + replay.attempts : 'No requests sent.');
        text('http-replay-response', replay.response || 'No response yet.');
        text('http-replay-effect', replay.effect || 'Task 9 exists: “Draft plan”.');
        text('http-send', replay.attempts ? 'Send the same request again' : 'Send request');
        root.querySelectorAll('[data-method]').forEach(function (button) {
            button.setAttribute('aria-pressed', String(button.dataset.method === replay.mode));
        });
    }

    function renderExport() {
        text('http-export-state', exporting.state);
        text('http-export-observed', exporting.observed || 'not yet read');
        text('http-export-request', exporting.request);
        text('http-export-response', exporting.response);
        text('http-export-note', exporting.message);
        text('http-export-submit', exporting.state === 'not submitted' ? 'Submit export' : 'Resubmit with the same key');
        root.querySelectorAll('[data-export-action]').forEach(function (button) {
            var action = button.dataset.exportAction;
            button.disabled = action === 'start' ? exporting.state !== 'queued'
                : action === 'succeed' || action === 'fail' ? exporting.state !== 'running'
                    : exporting.state === 'not submitted';
        });
    }

    function renderEdit() {
        text('http-server-title', editing.title);
        text('http-server-version', '"v' + editing.version + '"');
        ['a', 'b'].forEach(function (client) {
            text('http-version-' + client, '"v' + editing.clients[client].version + '"');
        });
        text('http-edit-request', editing.request || 'Both editors have read task 9 at ETag "v7".');
        text('http-edit-response', editing.response || 'No edit sent yet.');
        text('http-edit-note', editing.message || 'If-Match makes the write conditional on the version the editor read.');
    }

    root.addEventListener('click', function (event) {
        var button = event.target.closest('button');
        if (!button || !root.contains(button)) return;
        if (button.dataset.method) {
            replay = model.newReplay(button.dataset.method);
            renderReplay();
        } else if (button.id === 'http-send' || button.id === 'http-replay-reset') {
            replay = button.id === 'http-send' ? model.sendAgain(replay) : model.newReplay(replay.mode);
            renderReplay();
        } else if (button.id === 'http-export-reset') {
            exporting = model.newExport();
            renderExport();
        } else if (button.id === 'http-export-submit' || button.dataset.exportAction) {
            exporting = model.exportAction(exporting, button.dataset.exportAction || 'submit');
            renderExport();
        } else if (button.dataset.refresh) {
            var client = button.dataset.refresh;
            editing = model.refreshEdit(editing, client, el('http-draft-' + client).value);
            renderEdit();
        } else if (button.id === 'http-edit-reset') {
            editing = model.newEdit();
            ['a', 'b'].forEach(function (client) { el('http-draft-' + client).value = editing.clients[client].draft; });
            renderEdit();
        }
    });
    root.querySelectorAll('form[data-editor]').forEach(function (form) {
        form.addEventListener('submit', function (event) {
            event.preventDefault();
            var client = form.dataset.editor;
            editing = model.saveEdit(editing, client, el('http-draft-' + client).value);
            renderEdit();
        });
    });
    renderReplay();
    renderExport();
    renderEdit();
    root.querySelectorAll('[data-http-interactive]').forEach(function (element) { element.hidden = false; });
}());
