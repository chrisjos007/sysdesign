# Stream processing, event time, and correctness

ID: sd-30 | Level: Advanced | Stage 5: Reason about guarantees | Suggested study: 50 minutes

Prerequisites: sd-15, sd-16, sd-20, sd-25

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Separate event time from processing time and watermarks.
- Define a late-data policy for a windowed result.
- State the recovery boundary of an exactly-once processing claim.

## Intuition

A stream has no natural final page. To compute useful answers, a processor groups events into windows or maintains evolving state. Events may arrive late, repeat, or be replayed, so the answer needs a definition of both time and correctness.

## How it works

Event time represents when an event occurred; processing time reflects when a processor handles it. Watermarks express progress assumptions about event time and help decide when to emit windows; they are not proof that no late event can ever arrive. Multi-input operators must account for their inputs' progress and idle-source policy. Checkpoints preserve processing state and source positions for recovery. End-to-end exactly-once effects also require replayable input and a compatible transactional or idempotent output boundary.

Technical references: [Timely Stream Processing](https://nightlies.apache.org/flink/flink-docs-stable/docs/concepts/time/); [Stateful Stream Processing](https://nightlies.apache.org/flink/flink-docs-stable/docs/concepts/stateful-stream-processing/).

## Worked example

For lesson views in the window [10:00,10:05), events arrive at processing time 10:06 with event times 10:01 and 10:04. They belong to the earlier event-time window. If the processor already emitted a result, policy may update it, send corrections, or route late data to a separate path. A dashboard should indicate whether a count is provisional or final under that policy. Replaying the input must not increment an external result twice.

## Trade-offs and failure modes

Waiting longer for late events improves completeness but increases result latency and state retention. Aggressive watermarks give faster results while excluding or correcting more late data. An idle input can hold back progress unless handled explicitly; incorrectly marking it idle can make returning records late. Checkpoint overhead, large state, skewed keys, and slow sinks affect recovery. Deterministic business logic and versioned external lookups matter when replay must reproduce an answer.

## Practice

Design a per-course daily completion count from events that can arrive 48 hours late and may be duplicated. Define keys, event identity, window timezone, watermark policy, output revisions, and a replay procedure.

### Answer guidance

Use stable completion-event IDs and an explicit event-time/timezone contract. Deduplicate within a retention horizon covering replay/lateness, or make the output operation idempotent over durable event identity. Retain or rebuild enough state to correct late arrivals. Write versioned/upserted window results and expose revision status. Reprocessing into a new output version followed by verification can avoid mixing a historical rebuild with live increments.

## Knowledge check

### 1. Does a watermark make later arrival of older events impossible?

No. It represents the processor's progress assumption; the system still needs a late-data policy.

### 2. Does restoring a checkpoint undo an email already sent by a sink?

No. External effects require their own transactional, idempotent, or compensating treatment.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Timely Stream Processing](https://nightlies.apache.org/flink/flink-docs-stable/docs/concepts/time/)
- [Stateful Stream Processing](https://nightlies.apache.org/flink/flink-docs-stable/docs/concepts/stateful-stream-processing/)

