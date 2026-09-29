(function () {
    'use strict';
    var root = document.getElementById('latency-lesson');
    var model = window.LatencyModel;
    if (!root || !model) return;
    var queue = model.newQueue();
    function el(id) { return document.getElementById('latency-' + id); }
    function text(id, value) { el(id).textContent = value; }
    function number(id) { return Number(el(id).value); }
    function format(value) { return value.toLocaleString('en-US', {maximumFractionDigits: 2}); }
    function renderQueue() {
        var arrivals = number('arrivals'), capacity = number('capacity');
        text('arrivals-value', arrivals);
        text('capacity-value', capacity);
        text('queue-summary', format(queue.seconds / 60) + ' minutes elapsed. ' + format(queue.backlog) + ' jobs waiting. ' +
            (queue.seconds ? 'Last interval completed throughput: ' + format(queue.throughput) + ' jobs/s.' : 'No interval completed yet.'));
        text('totals', 'Total arrivals: ' + format(queue.arrived) + ' jobs. Total completions: ' + format(queue.completed) + ' jobs.');
        var drain = model.drainSeconds(queue.backlog, arrivals, capacity);
        text('drain', queue.backlog === 0
            ? 'The queue is empty. ' + (arrivals > capacity ? 'At these rates, it will grow by ' + (arrivals - capacity) + ' jobs/s.' : 'These rates keep it empty in this smooth-arrival model.')
            : Number.isFinite(drain) ? 'At these rates, clearing the backlog takes ' + format(drain) + ' seconds (' + format(drain / 60) + ' minutes).'
                : 'The backlog cannot drain at these rates. ' + (arrivals === capacity ? 'Arrivals use all capacity.' : 'It grows by ' + (arrivals - capacity) + ' jobs/s.'));
    }
    function renderLittle() {
        var throughput = number('throughput'), mean = number('mean');
        text('throughput-value', throughput);
        text('mean-value', mean);
        text('concurrency', throughput + ' requests/s × ' + format(mean / 1000) + ' s = ' + format(model.concurrency(throughput, mean)) + ' requests in flight on average.');
    }
    function renderTail(count) {
        var result = model.tail(count);
        text('distribution-label', result.fastCount + ' requests at 20 ms · ' + count + ' requests at 2,000 ms');
        el('fast-bar').style.width = result.fastCount / 10 + '%';
        el('slow-bar').style.width = count / 10 + '%';
        text('tail-mean', format(result.mean) + ' ms');
        ['p50', 'p99', 'p999'].forEach(function (key) { text(key, format(result[key]) + ' ms'); });
        text('tail-note', result.p99 === 20 ? 'p99 selects sorted request 990: still a fast request. The ten slow requests remain real.'
            : 'p99 selects sorted request 990: now a slow request. The mean is still below 60 ms, despite twenty 2-second waits.');
        root.querySelectorAll('[data-slow]').forEach(function (button) { button.setAttribute('aria-pressed', String(Number(button.dataset.slow) === count)); });
    }
    root.addEventListener('input', function (event) {
        if (event.target.id === 'latency-arrivals' || event.target.id === 'latency-capacity') renderQueue();
        if (event.target.id === 'latency-throughput' || event.target.id === 'latency-mean') renderLittle();
    });
    root.addEventListener('click', function (event) {
        var button = event.target.closest('button');
        if (!button || !root.contains(button)) return;
        if (button.dataset.slow) { renderTail(Number(button.dataset.slow)); return; }
        if (button.id === 'latency-reset') {
            queue = model.newQueue(); el('arrivals').value = 120; el('capacity').value = 100;
        } else if (button.id === 'latency-minute' || button.id === 'latency-five') {
            queue = model.advance(queue, number('arrivals'), number('capacity'), button.id === 'latency-five' ? 300 : 60);
        } else return;
        renderQueue();
    });
    renderQueue(); renderLittle(); renderTail(10);
    root.querySelectorAll('[data-latency-interactive]').forEach(function (element) { element.hidden = false; });
}());
