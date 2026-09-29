# Service objectives and error budgets

ID: sd-19 | Level: Advanced | Stage 4: Operate reliably | Suggested study: 35 minutes

Prerequisites: sd-03, sd-06, sd-18

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Define good and eligible events for an SLI.
- Calculate an event-based error budget and burn rate.
- Connect reliability measurements to operational decisions.

## Intuition

Reliability becomes useful when it describes what users can accomplish. A machine being alive does not prove that a learner can open a lesson or submit an answer. A service-level indicator measures a behavior; an objective states the target and window.

## How it works

For an event-based SLI, define eligible events and which count as good. An SLO specifies the required good-event fraction over a window. The error budget is the allowed bad fraction, 1 - target, multiplied by eligible events for a fixed observed volume. Burn rate compares the observed bad fraction with the allowed bad fraction. SLOs should guide decisions such as slowing releases, repairing a dependency, or changing a capacity limit, rather than merely decorating a dashboard.

Technical references: [Implementing SLOs](https://sre.google/workbook/implementing-slos/).

## Worked example

A lesson-read SLO requires 99.9% of eligible requests to succeed within 500 ms over 30 days. If that window contains 10 million eligible requests, at most 10,000 can be bad. In an interval with a 1% bad fraction, burn rate is 0.01 / 0.001 = 10. If traffic volume is uniform and that behavior persists, a fresh 30-day budget would be consumed in roughly three days. With variable traffic, the event counts, not wall-clock extrapolation alone, determine consumption.

## Trade-offs and failure modes

Define whether client cancellations, invalid input, deliberate shedding, and dependency failures count; silently excluding painful failures makes the metric misleading. Request-weighted objectives can hide failures concentrated in a small tenant. Use meaningful dimensions without creating an unmanageable objective per user. Low-volume services may need synthetic checks and longer windows. Time-based availability budgets and event-based budgets are not interchangeable.

## Practice

A dashboard endpoint returns HTTP 200 quickly but omits the learner's saved progress in 2% of responses. Decide whether the endpoint is healthy, and define an indicator that reflects the product behavior.

### Answer guidance

A status-code-only indicator misses the failure. Define success to include the required progress data or monitor the critical user journey separately. Count malformed or incomplete responses as bad when they violate the declared contract. Compare the observed fraction with an explicitly chosen objective rather than declaring health from latency alone.

## Knowledge check

### 1. For a 99.5% target and 200,000 eligible events, how many bad events are allowed?

1,000: 200,000 × 0.005.

### 2. Is an error budget permission to ignore all errors below the threshold?

No. It is a decision tool; severe correctness, security, or concentrated user failures may require action regardless of aggregate budget.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Implementing SLOs](https://sre.google/workbook/implementing-slos/)

