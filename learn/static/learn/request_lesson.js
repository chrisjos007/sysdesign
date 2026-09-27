/* sd-01: a latency comparison, not a network simulator or scored activity. */
(function () {
    'use strict';
    var root = document.getElementById('request-lesson');
    var data = document.getElementById('request-lesson-data');
    if (!root || !data) return;
    var lesson = JSON.parse(data.textContent);
    var controls = document.getElementById('request-connection-controls');
    var scenarios = {
        cold: {
            skipped: [],
            note: 'No cached answer or open connection. All four stages contribute to the total.'
        },
        cached: {
            skipped: ['dns'],
            note: 'A valid DNS answer saves 20 ms. A new TCP connection and TLS handshake are still needed.'
        },
        reused: {
            skipped: ['dns', 'tcp', 'tls'],
            note: 'A valid established connection saves 100 ms of setup. Only the request and response remain in this model.'
        }
    };

    function compare(name) {
        var scenario = scenarios[name];
        var total = 0;
        var equation = [];
        lesson.steps.forEach(function (step) {
            var skipped = scenario.skipped.indexOf(step.key) !== -1;
            var cost = skipped ? 0 : step.ms;
            total += cost;
            if (!skipped) equation.push(cost + ' ' + step.title);
            root.querySelector('[data-cost="' + step.key + '"]').textContent = skipped ? '0 ms · reused' : cost + ' ms';
            root.querySelector('[data-step="' + step.key + '"]').classList.toggle('is-reused', skipped);
            root.querySelector('[data-bar="' + step.key + '"]').style.flexGrow = cost;
        });
        document.getElementById('request-total').textContent = total + ' ms';
        document.getElementById('request-equation').textContent = equation.join(' + ');
        document.getElementById('request-scenario-note').textContent = scenario.note;
        controls.querySelectorAll('button').forEach(function (button) {
            button.setAttribute('aria-pressed', String(button.dataset.connection === name));
        });
    }

    controls.addEventListener('click', function (event) {
        var button = event.target.closest('button[data-connection]');
        if (button && controls.contains(button)) compare(button.dataset.connection);
    });
    controls.hidden = false;
}());
