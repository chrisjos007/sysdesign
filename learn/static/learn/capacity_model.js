/* Decimal units and original teaching assumptions; not a sizing recommendation. */
(function (root, factory) {
    'use strict';
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.CapacityModel = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';
    function estimate(users, peakFactor, retentionDays) {
        if (![users, peakFactor, retentionDays].every(Number.isSafeInteger) ||
            users < 0 || users > 1000000 || peakFactor < 1 || peakFactor > 100 ||
            retentionDays < 1 || retentionDays > 3650) throw new RangeError('Invalid workload assumptions');
        const dailyReads = users * 20;
        const averageRps = dailyReads / 86400;
        const peakRps = averageRps * peakFactor;
        const eventBytesPerDay = users * 5 * 500;
        return {dailyReads, averageRps, peakRps,
            payloadGB: dailyReads * 10000 / 1e9,
            peakMbps: peakRps * 10000 * 8 / 1e6,
            eventMB: eventBytesPerDay / 1e6,
            storageGB: eventBytesPerDay * retentionDays / 1e9};
    }
    function fleet(peakRps, perServer, failedServers) {
        if (!Number.isFinite(peakRps) || peakRps < 0 || !Number.isFinite(perServer) || perServer <= 0 ||
            !Number.isSafeInteger(failedServers) || failedServers < 0 || failedServers > 1) {
            throw new RangeError('Invalid capacity assumptions');
        }
        const serving = Math.ceil(peakRps / perServer);
        return {serving, provisioned: serving + failedServers};
    }
    return {estimate, fleet};
}));
