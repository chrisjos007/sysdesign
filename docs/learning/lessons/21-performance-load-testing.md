# Performance testing that exposes bottlenecks

ID: sd-21 | Stage 4: production | Suggested study: 40 minutes

Prerequisites: sd-03, sd-06, sd-09, sd-18, sd-19

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Choose a workload model that matches user behavior.
- Measure offered load as well as successful throughput.
- Design a repeatable capacity and recovery experiment.

## Intuition

A load test is an experiment with a question, a workload, and a pass condition. 'The server survived 1,000 users' is incomplete unless you know what those users did, how often they did it, and what experience they received.

## How it works

In a closed model, virtual users wait for an iteration to finish before starting another; slowdown can reduce the arrival rate. In an open model, new work is scheduled independently of completion. Grafana k6 explains how a closed model can hide overload through coordinated omission. Neither model is universally correct: select the one matching the workload. Always observe generator capacity, scheduled versus achieved arrivals, dropped iterations, errors, latency distributions, and downstream saturation.

Technical references: [Open and Closed Models](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/).

## Worked example

Assume 100 virtual users each submit one request and immediately repeat. At 100 ms response time they can offer roughly 1,000/s, ignoring client overhead. At one second response time they offer only about 100/s. The service slowdown has reduced test pressure tenfold. If real arrivals remain at 1,000/s regardless, this experiment understates queue growth. An arrival-rate test should preserve the intended demand or clearly report when the generator cannot.

## Trade-offs and failure modes

Warm caches and tiny datasets can produce optimistic results. Uniform keys miss hot tenants and popular items. Stress tests find limits; soak tests expose growth, leaks, and maintenance effects; recovery tests measure the return to health after overload or failure. Test environments differ from production, so report the boundary of the evidence. Do not infer a universal capacity number from one run.

## Practice

Plan a capacity experiment for a learning API: read-heavy traffic, occasional submissions, one hot course, a cold-cache interval, and loss of one application instance. Specify pass criteria and measurements.

### Answer guidance

Use a documented request mix, realistic payload/data distributions, and staged offered load. Define latency and bad-event targets per critical operation, plus bounded pool waiting and queue age. Run the cold-cache and instance-loss phases deliberately, then measure recovery. Check load-generator headroom. A passing normal phase does not excuse failure during the required degraded mode.

## Knowledge check

### 1. Why can a constant-virtual-user test hide overload?

As responses slow, each virtual user sends fewer requests, reducing the offered arrival rate.

### 2. What must accompany a throughput result?

Workload assumptions, offered load, latency/error outcomes, environment, and relevant resource or dependency limits.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Open and Closed Models](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/)

