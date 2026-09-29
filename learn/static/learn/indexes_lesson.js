(function () {
    'use strict';
    const root = document.getElementById('indexes-lesson');
    if (!root || !window.IndexesModel) return;
    const model = window.IndexesModel;
    const get = id => root.querySelector('#indexes-' + id);
    const names = {scan: 'Sequential scan', tenant: 'Tenant index', composite: 'Composite index'};
    function renderAccess() {
        const path = get('path').value;
        const result = model.compare(get('workload').value, path);
        get('summary').textContent = `${names[path]}: examine ${result.examined.toLocaleString('en-US')} ${path === 'scan' ? 'table rows' : 'index entries'}, sort ${result.sortInput} matches, return ${result.returned} orders.`;
        get('explanation').textContent = path === 'composite'
            ? 'Both equality filters locate one range. Read it in the requested order with no separate sort, stopping at the limit or range end.'
            : path === 'tenant' ? 'Skip other tenants, but inspect all 100 entries for this tenant and sort the open orders before applying the limit.'
            : 'The limit bounds the answer, but this path still checks the whole table before sorting its matches.';
        get('steps').replaceChildren();
        result.steps.forEach(text => {
            const li = document.createElement('li');
            li.textContent = text;
            get('steps').appendChild(li);
        });
        get('ids').textContent = result.ids.join(', ');
    }
    function renderPlan() {
        const estimated = Number(get('estimate').value);
        const result = model.planRows(estimated, 10, 50);
        get('plan').textContent = `Index Scan on orders (rows=${estimated})\n  (actual rows=10 loops=50)`;
        get('plan-result').textContent = `Actual output is ${result.factor}× the estimate per execution; ${result.total} rows are emitted across 50 loops.`;
    }
    function renderQueries() {
        const projects = Number(get('projects').value);
        const count = model.queryCount(projects, get('fetch').value);
        get('query-result').textContent = `${projects} ${projects === 1 ? 'project' : 'projects'} → ${count} ${count === 1 ? 'query' : 'queries'}.`;
    }
    ['path', 'workload'].forEach(id => get(id).addEventListener('change', renderAccess));
    get('estimate').addEventListener('change', renderPlan);
    ['projects', 'fetch'].forEach(id => get(id).addEventListener('change', renderQueries));
    renderAccess(); renderPlan(); renderQueries();
    root.querySelectorAll('[data-indexes-interactive]').forEach(element => { element.hidden = false; });
}());
