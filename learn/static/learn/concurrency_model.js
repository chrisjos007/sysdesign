/* Deterministic teaching interleavings, not a database or thread scheduler. */
(function (root, factory) {
    'use strict';
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.ConcurrencyModel = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';
    const modes = ['unsafe', 'shared-lock', 'separate-locks', 'atomic'];
    function create(mode = 'unsafe') {
        if (!modes.includes(mode)) throw new RangeError('Unknown synchronization mode');
        return {mode, balance: 10, owner: null, workers: [{phase: 0, local: null}, {phase: 0, local: null}], history: []};
    }
    function step(state, index) {
        if (index !== 0 && index !== 1) throw new RangeError('Unknown worker');
        const next = {...state, workers: state.workers.map(w => ({...w})), history: state.history.slice()};
        const worker = next.workers[index];
        const name = index === 0 ? 'A' : 'B';
        if (worker.phase === 3) return next;
        let event;
        if (next.mode === 'shared-lock' && next.owner !== null && next.owner !== index) {
            event = `Worker ${name} waits: the other worker holds the shared lock. Advance that worker to release it.`;
        } else if (next.mode === 'atomic') {
            next.balance += 1;
            worker.phase = 3;
            event = `Worker ${name} atomically increments the stored balance to ${next.balance}.`;
        } else if (worker.phase === 0) {
            if (next.mode === 'shared-lock') next.owner = index;
            worker.local = next.balance;
            worker.phase = 1;
            event = `Worker ${name} reads ${worker.local} into its local copy.`;
        } else if (worker.phase === 1) {
            worker.local += 1;
            worker.phase = 2;
            event = `Worker ${name} calculates ${worker.local} locally. Stored balance is still ${next.balance}.`;
        } else {
            next.balance = worker.local;
            worker.phase = 3;
            if (next.mode === 'shared-lock') next.owner = null;
            event = `Worker ${name} writes ${next.balance}${next.mode === 'shared-lock' ? ' and releases the shared lock' : ''}.`;
        }
        next.history.push(event);
        return next;
    }
    return {create, step};
}));
