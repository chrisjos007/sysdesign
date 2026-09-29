(function () {
    'use strict';
    const root = document.getElementById('concurrency-lesson');
    if (!root || !window.ConcurrencyModel) return;
    const model = window.ConcurrencyModel;
    const mode = root.querySelector('#concurrency-mode');
    const buttons = Array.from(root.querySelectorAll('[data-worker]'));
    let state = model.create();
    const notes = {
        unsafe: 'The read and write are separate operations. Each worker can overwrite the other’s result.',
        'shared-lock': 'Both workers use the same lock. It protects all three steps; the waiting worker can continue after the owner writes.',
        'separate-locks': 'A and B run on different servers, each with its own lock. Neither lock stops the other server from changing the shared balance.',
        atomic: 'Each click applies balance = balance + 1 at the database. No stale local value is written back.'
    };
    function render() {
        const done = state.workers.filter(w => w.phase === 3).length;
        root.querySelector('#concurrency-mode-note').textContent = notes[state.mode];
        root.querySelector('#concurrency-balance').textContent = `Stored balance: ${state.balance} · Expected after both increments: 12`;
        let result = done === 2
            ? (state.balance === 12 ? 'Both increments are present. Try another order to test the protection.' : 'Lost update: both workers finished, but only one increment remains.')
            : `${done} of 2 workers finished. Choose the next step.`;
        if (state.history.length) result = state.history[state.history.length - 1] + ' ' + result;
        root.querySelector('#concurrency-result').textContent = result;
        buttons.forEach((button, index) => {
            const w = state.workers[index];
            const waiting = state.mode === 'shared-lock' && state.owner !== null && state.owner !== index;
            button.disabled = w.phase === 3;
            button.textContent = `${index === 0 ? 'A' : 'B'}: ${w.phase === 3 ? 'Finished' : waiting ? 'Try the shared lock' : state.mode === 'atomic' ? 'Increment atomically' : ['Read balance', 'Calculate +1', 'Write balance'][w.phase]}`;
            root.querySelector('#concurrency-worker-' + index).textContent = `Local copy: ${w.local === null ? 'not read' : w.local}${waiting ? ' · Waiting for lock' : ''}`;
        });
        const history = root.querySelector('#concurrency-history');
        history.replaceChildren();
        (state.history.length ? state.history : ['No steps yet. Choose either worker.']).forEach(event => {
            const item = document.createElement('li');
            item.textContent = event;
            history.appendChild(item);
        });
    }
    buttons.forEach(button => button.addEventListener('click', () => {
        state = model.step(state, Number(button.dataset.worker));
        render();
    }));
    function reset() { state = model.create(mode.value); render(); }
    mode.addEventListener('change', reset);
    root.querySelector('#concurrency-reset').addEventListener('click', reset);
    render();
    root.querySelectorAll('[data-concurrency-interactive]').forEach(element => { element.hidden = false; });
}());
