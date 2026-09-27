# Concurrency, parallelism, and shared state

ID: sd-04 | Stage 1: beginner | Suggested study: 30 minutes

Prerequisites: sd-03

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Distinguish concurrent progress from simultaneous execution.
- Demonstrate a lost update with an execution timeline.
- Choose bounded work and an appropriate synchronization boundary.

## Intuition

Concurrency means several tasks are in progress during overlapping periods. Parallelism means work runs simultaneously. A waiter can handle several tables concurrently without being in two places at once. The useful question is where tasks wait and what state they share.

## How it works

An event loop can switch among cooperative tasks when they yield; calling a blocking function directly can stop that loop from serving other work. Python's asyncio provides tasks and structured task groups, but async syntax does not make CPU work parallel. Shared state can race across threads, processes, or separate server instances. A process-local lock coordinates only that process. Database constraints, atomic updates, or transactions can enforce rules at the shared storage boundary.

Technical references: [Coroutines and Tasks](https://docs.python.org/3/library/asyncio-task.html); [Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html).

## Worked example

Two workers both read remaining_seats = 1. Each checks that a seat is available, then each writes 0 and issues a different ticket. The final number looks plausible while two tickets exist. Instead, execute a conditional database update that decrements only if remaining_seats > 0, check that exactly one row changed, and create the reservation in the same transaction. This example introduces atomicity: the group of related writes commits together or does not take effect.

## Trade-offs and failure modes

Locks simplify some reasoning but can introduce contention and deadlocks. Optimistic version checks work well when conflicts are infrequent but require retries when they occur. An async worker per input can exhaust memory or downstream connections; bound the number in flight. A canceled coroutine may have already triggered an external effect, so local cancellation is not proof of remote rollback.

## Practice

Write a six-step interleaving in which two balance increments lose one increment. Redesign it using an atomic increment. Then decide whether a lock stored in one web server protects the operation when a second server is added.

### Answer guidance

Both read 10, both calculate 11, and both write 11: two increments produce only one net increase. An atomic update of balance = balance + 1 lets the database serialize conflicting changes. A local lock is insufficient once requests can reach another process; the shared authority must enforce the update rule.

## Knowledge check

### 1. Does adding await make a CPU-heavy loop run in parallel?

No. It enables suspension at appropriate operations; CPU parallelism requires an execution model that supports it.

### 2. When is a local mutex insufficient for an inventory rule?

When other processes or services can update the same inventory without participating in that mutex.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Coroutines and Tasks](https://docs.python.org/3/library/asyncio-task.html)
- [Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)

