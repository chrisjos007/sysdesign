# Timeouts, retries, and jitter

ID: sd-13 | Level: Advanced | Stage 3: Handle distributed failures | Suggested study: 35 minutes

Prerequisites: sd-02, sd-03, sd-10

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Allocate an end-to-end deadline across attempts and waiting.
- Explain retry amplification across service layers.
- Choose retry eligibility, limits, and randomized delays.

## Intuition

A timeout is the caller deciding it has waited long enough. It is not a message from the server saying nothing happened. Retrying can recover from temporary faults, but every retry adds work precisely when a dependency may already be struggling.

## How it works

Use a total deadline as well as per-attempt connection and request limits. Account for waiting, DNS/setup behavior in the client, and time spent in dependencies. Bound retries by attempts, elapsed time, and a load budget. Exponential backoff increases waiting between attempts; jitter spreads clients across different retry times. Retry only errors and operations whose contracts permit it, honor server guidance where appropriate, and coordinate retries across layers. Idempotency protects repeated effects; it does not eliminate extra load.

Technical references: [Control and Limit Retry Calls](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html); [Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/).

## Worked example

A request has a 1,000 ms total deadline. Attempt one uses 300 ms, the client waits 100 ms, and attempt two uses 400 ms: only 200 ms remain for additional work and returning a response. Starting another 400 ms attempt violates that budget. Separately, if each of three nested layers makes up to three attempts, one incoming request can generate up to 3 × 3 × 3 = 27 calls to the deepest dependency. One retry owner or a propagated retry budget prevents this multiplication.

## Trade-offs and failure modes

An aggressive timeout rejects legitimate slow work; an excessive one retains scarce resources. Fixed retry intervals synchronize clients after an outage. Unlimited backoff still permits unlimited total waiting. Cancellation propagation saves resources where supported, but a remote operation may already have committed. A circuit breaker can reduce calls to a failing dependency, yet requires a bounded probe/recovery policy and does not replace concurrency limits.

## Practice

Propose a retry policy for reading a public profile and for creating a payment operation. Include retryable conditions, operation identity, an overall deadline, an attempt cap, and what is shown when the deadline expires.

### Answer guidance

The read can retry selected transient failures within a bounded budget. The payment must reuse a stable operation key and query/reconcile uncertain outcomes rather than create a new payment blindly. In both paths, select timeouts from measured behavior and the user deadline, add randomized bounded delays, and report unavailable or pending/unknown honestly after the budget expires.

## Knowledge check

### 1. If every layer retries three times, is the deepest service called only three times?

No. Nested attempts can multiply; three layers with three attempts each can produce 27 calls.

### 2. Does a timeout authorize treating a payment as failed?

No. The operation may have committed; inspect durable state or reconcile using the original operation identity.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Control and Limit Retry Calls](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html)
- [Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)

