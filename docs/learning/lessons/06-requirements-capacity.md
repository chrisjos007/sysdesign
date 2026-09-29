# Requirements and capacity: turn assumptions into numbers

ID: sd-06 | Level: Beginner | Stage 1: Understand a request | Suggested study: 35 minutes

Prerequisites: sd-02, sd-03, sd-05

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Separate user behavior, invariants, and performance targets.
- Estimate traffic, storage, and bandwidth with stated units.
- Identify which assumption could change the architecture.

## Intuition

A design begins with questions about the product. 'Support a million users' does not tell you whether those users read once a month or upload videos every minute. Estimates are useful when they expose a bottleneck or a question worth measuring.

## How it works

Write down actions, request sizes, active-user assumptions, retention, access patterns, and acceptable failure behavior. Distinguish an invariant, such as never confirming two owners of one seat, from an objective, such as 99% of accepted reads finishing within 300 ms. State measurement windows and exclusions. Estimate steady and peak demand separately, then test representative workloads; resource limits and business targets must meet in a measurable contract.

Technical references: [Service Level Objectives](https://sre.google/sre-book/service-level-objectives/); [Open and Closed Models](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/).

## Worked example

Assume 100,000 daily active learners each load 20 lessons/day. That is 2 million reads/day, or about 23.15 reads/s averaged over 86,400 seconds. An assumed 20× peak gives about 463 reads/s. At 10 KB of response data per read, average daily payload is 20 GB using decimal units, before headers and compression. If users submit five 500-byte events/day, raw event storage is 250 MB/day or 7.5 GB/30 days, before indexes, replicas, and backups.

## Trade-offs and failure modes

Daily averages conceal synchronized exams or notification-driven bursts. Replication and backups multiply different portions of storage; they are not one arbitrary universal multiplier. A cache may reduce origin reads without reducing bytes delivered to users. Capacity for one failed node matters if the service must survive that failure. Cost estimates should use measured resource quantities and separately dated provider prices.

## Practice

The same learning service must now retain events for 365 days and handle 40× average peak traffic. Recalculate raw event storage and peak reads. Name two observations you need before choosing the number of application servers.

### Answer guidance

Raw event storage becomes 91.25 GB using decimal units. Peak reads become about 926/s. Measure the throughput a server sustains at the required latency/error objectives and the downstream database/cache demand for a realistic request mix. Include failure headroom rather than dividing by an untested requests-per-server guess.

## Knowledge check

### 1. Is 'one million registered users' enough for a capacity estimate?

No. You need activity, actions per active user, timing, payloads, and retention assumptions.

### 2. Which assumption changes first when a flash crowd appears?

The peak arrival pattern and concurrency; the registered-user count may remain unchanged.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Open and Closed Models](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/)

