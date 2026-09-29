(function () {
    'use strict';
    const root = document.getElementById('capacity-lesson');
    if (!root || !window.CapacityModel) return;
    const get = id => root.querySelector('#capacity-' + id);
    const number = id => Number(get(id).value);
    const fmt = value => value.toLocaleString('en-US', {maximumFractionDigits: 2});
    function render() {
        const result = window.CapacityModel.estimate(number('users'), number('peak'), number('retention'));
        get('reads').textContent = `${fmt(result.dailyReads)} reads/day ÷ 86,400 s/day = ${fmt(result.averageRps)} reads/s average.`;
        get('peak-result').textContent = `${fmt(result.averageRps)} × ${number('peak')} ≈ ${fmt(result.peakRps)} reads/s at peak.`;
        get('payload').textContent = `${fmt(result.payloadGB)} GB/day of response payload; ${fmt(result.peakMbps)} Mbit/s at peak.`;
        get('storage').textContent = `${fmt(result.eventMB)} MB/day × ${number('retention')} days = ${fmt(result.storageGB)} GB of raw events.`;
        if (get('throughput').value === 'unknown') {
            get('fleet').textContent = 'Server count is unknown. Measure sustainable throughput at the required latency and error targets first.';
        } else {
            const fleet = window.CapacityModel.fleet(result.peakRps, number('throughput'), number('failure'));
            get('fleet').textContent = `Round up ${fmt(result.peakRps)} ÷ ${number('throughput')} = ${fleet.serving} serving servers; add ${number('failure')} spare = ${fleet.provisioned} provisioned. This is a conditional lower bound, assuming even load and no shared bottleneck.`;
        }
    }
    root.querySelectorAll('select').forEach(select => select.addEventListener('change', render));
    get('reset').addEventListener('click', () => {
        root.querySelectorAll('select').forEach(select => { select.selectedIndex = 0; });
        render();
    });
    render();
    root.querySelectorAll('[data-capacity-interactive]').forEach(element => { element.hidden = false; });
}());
