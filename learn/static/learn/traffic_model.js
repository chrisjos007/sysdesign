/* Traffic Day's load model, in the browser. This is a line-for-line twin of
   learn/traffic.py: the page runs it to animate the day, and the server
   replays the same per-tick plan in Python to score it. Change one, change
   the other. */
(function () {
  'use strict';

  var TICKS = 144;
  var TICKS_PER_HOUR = 6;
  var REPEAT_SHARE_301 = 0.65;
  var CACHE_MISS = 0.15;
  var CACHE_MISS_HOT = 0.01;

  function circ(hr, center) {
    var x = Math.abs(hr - center) % 24;
    return Math.min(x, 24 - x);
  }

  function shape(hr) {
    return 0.35 + 1.15 * Math.exp(-(circ(hr, 20) ** 2) / 32)
      + 0.45 * Math.exp(-(circ(hr, 10) ** 2) / 8);
  }

  function spikeAt(hr, spike) {
    var start = spike.at_hour, hours = spike.hours;
    if (hr < start || hr >= start + hours) return 0;
    var x = (hr - start) / hours;
    var ramp = x < 0.15 ? x / 0.15 : x > 0.75 ? (1 - x) / 0.25 : 1;
    return spike.reads_per_sec * ramp;
  }

  function latency(base, util) {
    return util < 0.97 ? base / (1 - util) : base * 40;
  }

  window.TrafficModel = function (params) {
    function demand(i, redirect) {
      var hr = (i + 0.5) / TICKS_PER_HOUR;
      var f = shape(hr);
      var reads = params.reads_per_sec * f;
      var viral = spikeAt(hr, params.spike);
      var writes = params.writes_per_sec * f;
      if (redirect === 301) { reads *= REPEAT_SHARE_301; viral *= REPEAT_SHARE_301; }
      return { reads: reads, viral: viral, writes: writes, total: reads + viral + writes };
    }

    function simulateTick(i, cfg) {
      var d = demand(i, cfg.redirect);
      var cost = params.hourly_cost;
      var uApp = d.total / (cfg.servers * params.app_capacity);
      var dbReads = cfg.cache ? d.reads * CACHE_MISS + d.viral * CACHE_MISS_HOT : d.reads + d.viral;
      var nodes = 1 + cfg.replicas;
      var uDb = (d.writes + dbReads / nodes) / params.db_capacity;
      var touchDb = (dbReads + d.writes) / d.total;
      var mean = latency(8, uApp) + (cfg.cache ? 1 : 0) + touchDb * latency(12, uDb);
      var p99 = 2.5 * mean;
      var dropApp = uApp > 1 ? 1 - 1 / uApp : 0;
      var dropDb = uDb > 1 ? 1 - 1 / uDb : 0;
      var err = dropApp + (1 - dropApp) * touchDb * dropDb;
      var tickCost = (cfg.servers * cost.app + (cfg.cache ? cost.cache : 0) + nodes * cost.db) / TICKS_PER_HOUR;
      return {
        i: i, demand: d.total, capacity: cfg.servers * params.app_capacity, p99: p99, err: err, cost: tickCost,
        uApp: uApp, uDb: uDb, uReplica: cfg.replicas ? (dbReads / nodes) / params.db_capacity : 0,
        hitRate: cfg.cache ? 1 - dbReads / (d.reads + d.viral) : 0,
        breach: p99 > params.slo.p99_ms || err > params.slo.error_rate,
        cfg: { servers: cfg.servers, replicas: cfg.replicas, cache: cfg.cache, redirect: cfg.redirect }
      };
    }

    function hourlyCost(cfg) {
      var cost = params.hourly_cost;
      return cfg.servers * cost.app + (cfg.cache ? cost.cache : 0) + (1 + cfg.replicas) * cost.db;
    }

    return { TICKS: TICKS, TICKS_PER_HOUR: TICKS_PER_HOUR, demand: demand, simulateTick: simulateTick, hourlyCost: hourlyCost };
  };
})();
