/* Fluid estimates, not individual request scheduling or production measurements. */
(function (root, factory) {
    'use strict';
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.LatencyModel = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';
    function nonnegative(value) {
        if (!Number.isFinite(value) || value < 0) throw new RangeError('Expected a finite, nonnegative number');
        return value;
    }
    function newQueue() { return {seconds: 0, backlog: 0, arrived: 0, completed: 0, throughput: 0}; }
    function advance(state, arrivalRate, capacity, seconds) {
        [arrivalRate, capacity, seconds, state.backlog].forEach(nonnegative);
        if (!seconds) return Object.assign({}, state);
        var arrivals = arrivalRate * seconds;
        var completed = Math.min(state.backlog + arrivals, capacity * seconds);
        return {seconds: state.seconds + seconds, backlog: state.backlog + arrivals - completed,
            arrived: state.arrived + arrivals, completed: state.completed + completed, throughput: completed / seconds};
    }
    function drainSeconds(backlog, arrivalRate, capacity) {
        [backlog, arrivalRate, capacity].forEach(nonnegative);
        return backlog === 0 ? 0 : capacity > arrivalRate ? backlog / (capacity - arrivalRate) : Infinity;
    }
    function concurrency(throughput, meanMs) {
        return nonnegative(throughput) * nonnegative(meanMs) / 1000;
    }
    function tail(slowCount) {
        if (!Number.isInteger(slowCount) || slowCount < 0 || slowCount > 1000) throw new RangeError('Expected 0–1000 slow requests');
        var fastCount = 1000 - slowCount;
        function percentile(p) { return Math.ceil(p * 1000) <= fastCount ? 20 : 2000; }
        return {fastCount: fastCount, slowCount: slowCount, mean: (fastCount * 20 + slowCount * 2000) / 1000,
            p50: percentile(0.5), p99: percentile(0.99), p999: percentile(0.999)};
    }
    return {newQueue: newQueue, advance: advance, drainSeconds: drainSeconds, concurrency: concurrency, tail: tail};
}));
