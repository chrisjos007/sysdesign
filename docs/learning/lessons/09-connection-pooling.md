# Connection pooling and resource budgets

ID: sd-09 | Stage 2: intermediate | Suggested study: 30 minutes

Prerequisites: sd-03, sd-04, sd-07

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Budget connections across every process and replica.
- Distinguish pool waiting from database execution.
- Choose a pooling mode compatible with application state.

## Intuition

A pool reuses a limited number of established connections. Think of a fleet of taxis shared among requests: having more passengers does not mean creating one taxi for every passenger is efficient. The pool is both an optimization and an admission boundary.

## How it works

A request acquires a connection, uses it for a bounded operation, and returns it. Pool size, wait timeout, and connection lifetime are separate settings. Database-side poolers can multiplex application connections. PgBouncer session pooling reserves a server connection for a client session; transaction pooling releases it after a transaction. Session-dependent features do not all survive transaction pooling. Compatibility, including prepared statements, depends on the feature and configuration rather than a universal yes/no rule.

Technical references: [PgBouncer Features](https://www.pgbouncer.org/features.html).

## Worked example

Imagine 12 application instances, each with two worker processes and a local pool of 10 connections. The maximum application budget is 12 × 2 × 10 = 240 connections. A database with 200 allowed connections is already over budget before maintenance, background jobs, or rollout overlap. If a deployment temporarily doubles instances, potential demand becomes 480. A shared pooler can bound database connections, but its waiting queue still needs deadlines and capacity monitoring.

## Trade-offs and failure modes

A large pool can increase lock contention and database scheduling overhead. A tiny pool can leave useful database capacity idle. Long transactions hold connections even when the application is waiting elsewhere. Leaked connections eventually exhaust the pool. Transaction pooling can break code that assumes session-local settings persist; carry required state transactionally and verify the deployed pooler's supported features.

## Practice

Your API latency rises from 80 ms to 800 ms. Query execution remains near 50 ms, while pool acquisition takes 700 ms. Propose three investigations and explain why immediately increasing pool size may fail.

### Answer guidance

Check active transaction durations and leaks, aggregate process/replica connection budgets, and database saturation or lock waits. Also inspect background work and rollout overlap. More connections help only if the database has unused capacity and contention will not grow; otherwise they move the queue into the database and may worsen latency.

## Knowledge check

### 1. Does a pool timeout prove the database query ran slowly?

No. The request may never have obtained a connection or submitted a query.

### 2. Why include deployment overlap in connection budgets?

Old and new instances may run together, multiplying potential connections before the old fleet drains.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [PgBouncer Features](https://www.pgbouncer.org/features.html)

