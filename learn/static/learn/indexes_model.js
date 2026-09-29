/* Original teaching data and logical access paths, not a PostgreSQL cost model. */
(function (root, factory) {
    'use strict';
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else root.IndexesModel = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';
    const newestFirst = (a, b) => b.createdAt - a.createdAt || b.id - a.id;
    function orders(workload) {
        if (!['sparse', 'busy'].includes(workload)) throw new RangeError('Unknown workload');
        const open = workload === 'sparse' ? 10 : 90;
        return Array.from({length: 1000}, (_, i) => ({
            id: i + 1, tenant: i % 10 + 1,
            status: Math.floor(i / 10) < open ? 'open' : 'closed',
            createdAt: Math.floor(i / 30)
        }));
    }
    function compare(workload, path) {
        if (!['scan', 'tenant', 'composite'].includes(path)) throw new RangeError('Unknown access path');
        const rows = orders(workload);
        const tenant = rows.filter(row => row.tenant === 7);
        const matches = tenant.filter(row => row.status === 'open').sort(newestFirst);
        const result = matches.slice(0, 20);
        return {
            total: rows.length, tenantRows: tenant.length, matching: matches.length,
            examined: path === 'scan' ? rows.length : path === 'tenant' ? tenant.length : result.length,
            sortInput: path === 'composite' ? 0 : matches.length,
            returned: result.length, ids: result.map(row => row.id),
            steps: path === 'composite'
                ? ['Seek tenant 7 and open status in the composite index', 'Read newest entries first; stop at 20 or range end', 'Return matching orders']
                : [path === 'scan' ? 'Read every table row' : 'Find all entries for tenant 7', 'Keep only tenant 7 orders with open status', 'Sort matches by created_at DESC, id DESC', 'Return at most 20 orders']
        };
    }
    function planRows(estimated, actual, loops) {
        if (![estimated, actual, loops].every(Number.isSafeInteger) || estimated < 1 || actual < 0 || loops < 1) {
            throw new RangeError('Use positive integer estimates and loops, and nonnegative actual rows');
        }
        return {factor: actual / estimated, total: actual * loops};
    }
    function queryCount(projects, strategy) {
        if (!Number.isSafeInteger(projects) || projects < 1 || projects > 100) throw new RangeError('Choose 1–100 projects');
        if (!['individual', 'join', 'batch'].includes(strategy)) throw new RangeError('Unknown fetching strategy');
        return strategy === 'individual' ? projects + 1 : strategy === 'join' ? 1 : 2;
    }
    return {orders, compare, planRows, queryCount};
}));
