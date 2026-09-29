# Idempotency and deduplication

ID: sd-14 | Level: Advanced | Stage 3: Handle distributed failures | Suggested study: 40 minutes

Prerequisites: sd-02, sd-04, sd-13

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Define idempotency key scope, retention, and payload matching.
- Make duplicate claims and local effects atomic.
- Identify the boundary where an external effect escapes a transaction.

## Intuition

A duplicate request should mean 'continue or return the same operation,' not 'perform a new operation that happens to look similar.' Idempotency turns ambiguous retries into a protocol with a stable identity. Deduplication is one mechanism for implementing that protocol.

## How it works

A robust contract can key records by caller/tenant, operation type, and client-generated key. Store a fingerprint of relevant input and reject conflicting reuse. Recording the key, performing a local effect, and recording the result need an atomic boundary or a recoverable state machine. Concurrent duplicates must compete through a unique constraint or equivalent atomic claim. Retention is part of correctness: once a key expires, a sufficiently late duplicate may be treated as new. AWS describes caller-provided identifiers and parameter validation as ways to distinguish retries from new intent.

Technical references: [Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/); [Idempotent Requests](https://docs.stripe.com/api/idempotent_requests).

## Worked example

For a fictional credits service, transaction T inserts key (tenant7, award, abc), adds one credit award, and records its result. A unique constraint prevents transaction U from independently claiming the same key. If T commits but its response is lost, U can return the committed result. If T rolls back, its key and award both disappear. This pattern applies only when the key record and effect participate in the same transaction; sending an email inside T does not make the email transactional.

## Trade-offs and failure modes

Hashing request content alone can merge two intentional identical purchases. A reused key with changed input should not silently replay the wrong result. In-progress records need ownership, timeout/recovery, and status semantics; simply deleting a slow operation's key can allow duplicate execution. External providers need their own idempotency or queryable operation identity. Choose retention from the retry and replay horizon, then communicate it.

## Practice

Two identical requests arrive simultaneously while a worker performs a remote effect. Design the local states and describe what happens if the worker crashes after the remote success but before recording it locally.

### Answer guidance

Use a unique operation claim and explicit pending, succeeded, and terminal-failed states, with an uncertain/reconciling condition when appropriate. Send the same provider operation key on every attempt. After a crash, query the provider or safely repeat under its documented deduplication contract before marking the local result. A local pending row alone cannot prove whether the remote effect happened.

## Knowledge check

### 1. Is a content hash always a valid substitute for a client operation key?

No. Two intentionally separate operations may have identical payloads.

### 2. Why must retention be documented?

The duplicate-suppression guarantee only covers the period and scope for which identifying state remains available.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
- [Idempotent Requests](https://docs.stripe.com/api/idempotent_requests)

