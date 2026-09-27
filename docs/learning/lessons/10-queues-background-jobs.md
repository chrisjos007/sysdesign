# Queues and background jobs

ID: sd-10 | Stage 2: intermediate | Suggested study: 35 minutes

Prerequisites: sd-02, sd-03, sd-04

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Separate durable acceptance from successful completion.
- Place acknowledgements relative to business effects.
- Estimate backlog growth and recovery capacity.

## Intuition

A queue decouples accepting work from performing it. This makes brief bursts easier to handle and allows workers to scale independently. It also introduces a new promise: accepted work must remain observable until it succeeds, expires under policy, or fails visibly.

## How it works

A producer publishes a job; the broker makes it available; a worker performs it and acknowledges it. RabbitMQ publisher confirms concern broker acceptance, while consumer acknowledgements concern handling of deliveries; one does not imply the other. Acknowledging before a durable business effect can lose work after a crash. Acknowledging after it can allow duplicate effects if the worker crashes between commit and acknowledgement. The usual design combines durable acceptance, retryable work, and duplicate handling.

Technical references: [Consumer Acknowledgements and Publisher Confirms](https://www.rabbitmq.com/docs/confirms).

## Worked example

An export API stores an operation ID and arranges durable job publication, then returns 202. A worker writes a report to a versioned object key and marks that operation complete. With 600 jobs/min arriving and 10 workers each processing one job/s, total capacity is also 600/min: there is no spare capacity to clear a backlog. If 1,200/min arrive for ten minutes, 6,000 jobs accumulate. At 15 workers and normal arrivals, the spare 300/min takes 20 minutes to drain them.

## Trade-offs and failure modes

Retries can recover transient errors but repeatedly retrying malformed input wastes capacity. Use attempt limits, classification, and a visible dead-letter or failed-job path. Monitor oldest-job age as well as count: ten expensive jobs may be worse than a thousand cheap ones. Separate urgent work from large batch jobs when their service objectives differ. A queue cannot absorb unlimited sustained overload.

## Practice

List the outcomes of crashes before the business commit, after commit but before acknowledgement, and after acknowledgement. Design an operation record that makes each outcome understandable to the user.

### Answer guidance

Before commit, work should become retryable. After commit but before acknowledgement, a repeat must recognize the existing result. After acknowledgement, the result must already be durably discoverable. Store a stable operation ID, status, result reference, and relevant failure information; make status transitions conditional so stale workers cannot overwrite newer outcomes.

## Knowledge check

### 1. Does a publisher confirm mean the report has been generated?

No. It concerns publication, not successful consumer-side report generation.

### 2. Why is oldest-job age a useful metric?

It directly exposes how long accepted work has waited, while count alone ignores job cost and arrival patterns.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Consumer Acknowledgements and Publisher Confirms](https://www.rabbitmq.com/docs/confirms)

