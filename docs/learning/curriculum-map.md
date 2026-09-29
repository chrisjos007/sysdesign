# Curriculum map

Use this as a guided sequence, or follow only the prerequisites for a selected lesson. IDs are stable catalogue identifiers; the rows link directly to the documents. The path has five stages, and every stage belongs to one of three levels: stage 1 is Beginner, stage 2 is Intermediate, and stages 3 to 5 and the case studies are Advanced ([content standards](CONTENT_STANDARDS.md)). Levels describe learning progression, not application unlock levels.

## 1. Beginner — Understand a request

Trace one user request, derive a measurable requirement, and explain the first resource bottleneck without guessing a server count.

| ID | Lesson | Prerequisites | Minutes |
|---|---|---|---|
| sd-01 | [DNS, TCP, and TLS: follow a request](lessons/01-dns-tcp-tls.md) | None | 25 |
| sd-02 | [HTTP and API design: define the contract](lessons/02-http-api-design.md) | [sd-01](lessons/01-dns-tcp-tls.md) | 25 |
| sd-03 | [Latency, throughput, and queueing](lessons/03-latency-throughput.md) | [sd-01](lessons/01-dns-tcp-tls.md) | 30 |
| sd-04 | [Concurrency, parallelism, and shared state](lessons/04-concurrency-basics.md) | [sd-03](lessons/03-latency-throughput.md) | 30 |
| sd-05 | [Indexes and query plans: read less data](lessons/05-indexes-query-plans.md) | [sd-03](lessons/03-latency-throughput.md), [sd-04](lessons/04-concurrency-basics.md) | 35 |
| sd-06 | [Requirements and capacity: turn assumptions into numbers](lessons/06-requirements-capacity.md) | [sd-02](lessons/02-http-api-design.md), [sd-03](lessons/03-latency-throughput.md), [sd-05](lessons/05-indexes-query-plans.md) | 35 |

Milestone: Trace one user request, derive a measurable requirement, and explain the first resource bottleneck without guessing a server count.

## 2. Intermediate — Scale a service

Design a service with bounded resource use, clear cache freshness, durable background work, and predictable collection traversal.

| ID | Lesson | Prerequisites | Minutes |
|---|---|---|---|
| sd-07 | [Load balancing, health checks, and draining](lessons/07-load-balancing-health.md) | [sd-01](lessons/01-dns-tcp-tls.md), [sd-03](lessons/03-latency-throughput.md), [sd-06](lessons/06-requirements-capacity.md) | 30 |
| sd-08 | [Caching, invalidation, and stampedes](lessons/08-caching-invalidation.md) | [sd-02](lessons/02-http-api-design.md), [sd-03](lessons/03-latency-throughput.md), [sd-05](lessons/05-indexes-query-plans.md) | 35 |
| sd-09 | [Connection pooling and resource budgets](lessons/09-connection-pooling.md) | [sd-03](lessons/03-latency-throughput.md), [sd-04](lessons/04-concurrency-basics.md), [sd-07](lessons/07-load-balancing-health.md) | 30 |
| sd-10 | [Queues and background jobs](lessons/10-queues-background-jobs.md) | [sd-02](lessons/02-http-api-design.md), [sd-03](lessons/03-latency-throughput.md), [sd-04](lessons/04-concurrency-basics.md) | 35 |
| sd-11 | [Object storage, delivery, and CDNs](lessons/11-object-storage-cdn.md) | [sd-01](lessons/01-dns-tcp-tls.md), [sd-02](lessons/02-http-api-design.md), [sd-08](lessons/08-caching-invalidation.md) | 30 |
| sd-12 | [Pagination and data access patterns](lessons/12-pagination-access-patterns.md) | [sd-02](lessons/02-http-api-design.md), [sd-05](lessons/05-indexes-query-plans.md), [sd-06](lessons/06-requirements-capacity.md) | 35 |
| sd-31 | [Partitioning, hot keys, and consistent hashing](lessons/31-partitioning-consistent-hashing.md) | [sd-05](lessons/05-indexes-query-plans.md), [sd-06](lessons/06-requirements-capacity.md), [sd-08](lessons/08-caching-invalidation.md) | 35 |

Milestone: Design a service with bounded resource use, clear cache freshness, durable background work, and predictable collection traversal.

## 3. Advanced — Handle distributed failures

Trace an ambiguous timeout or crash across state boundaries and show how the system recovers without violating its business rule.

| ID | Lesson | Prerequisites | Minutes |
|---|---|---|---|
| sd-13 | [Timeouts, retries, and jitter](lessons/13-timeouts-retries-jitter.md) | [sd-02](lessons/02-http-api-design.md), [sd-03](lessons/03-latency-throughput.md), [sd-10](lessons/10-queues-background-jobs.md) | 35 |
| sd-14 | [Idempotency and deduplication](lessons/14-idempotency-deduplication.md) | [sd-02](lessons/02-http-api-design.md), [sd-04](lessons/04-concurrency-basics.md), [sd-13](lessons/13-timeouts-retries-jitter.md) | 40 |
| sd-15 | [Delivery guarantees and ordering](lessons/15-delivery-ordering.md) | [sd-10](lessons/10-queues-background-jobs.md), [sd-14](lessons/14-idempotency-deduplication.md) | 40 |
| sd-16 | [Transactional outbox and change data capture](lessons/16-outbox-cdc.md) | [sd-05](lessons/05-indexes-query-plans.md), [sd-10](lessons/10-queues-background-jobs.md), [sd-14](lessons/14-idempotency-deduplication.md), [sd-15](lessons/15-delivery-ordering.md) | 40 |
| sd-17 | [Sagas and compensating actions](lessons/17-sagas-compensation.md) | [sd-14](lessons/14-idempotency-deduplication.md), [sd-15](lessons/15-delivery-ordering.md), [sd-16](lessons/16-outbox-cdc.md) | 40 |
| sd-18 | [Backpressure, load shedding, and graceful degradation](lessons/18-backpressure-load-shedding.md) | [sd-03](lessons/03-latency-throughput.md), [sd-07](lessons/07-load-balancing-health.md), [sd-09](lessons/09-connection-pooling.md), [sd-10](lessons/10-queues-background-jobs.md), [sd-13](lessons/13-timeouts-retries-jitter.md) | 35 |

Milestone: Trace an ambiguous timeout or crash across state boundaries and show how the system recovers without violating its business rule.

## 4. Advanced — Operate reliably

Define user-visible reliability, gather diagnostic evidence, release compatible changes, isolate tenants, and demonstrate recovery.

| ID | Lesson | Prerequisites | Minutes |
|---|---|---|---|
| sd-19 | [Service objectives and error budgets](lessons/19-slos-error-budgets.md) | [sd-03](lessons/03-latency-throughput.md), [sd-06](lessons/06-requirements-capacity.md), [sd-18](lessons/18-backpressure-load-shedding.md) | 35 |
| sd-20 | [Logs, metrics, traces, and useful observability](lessons/20-logs-metrics-traces.md) | [sd-07](lessons/07-load-balancing-health.md), [sd-10](lessons/10-queues-background-jobs.md), [sd-19](lessons/19-slos-error-budgets.md) | 35 |
| sd-21 | [Performance testing that exposes bottlenecks](lessons/21-performance-load-testing.md) | [sd-03](lessons/03-latency-throughput.md), [sd-06](lessons/06-requirements-capacity.md), [sd-09](lessons/09-connection-pooling.md), [sd-18](lessons/18-backpressure-load-shedding.md), [sd-19](lessons/19-slos-error-budgets.md) | 40 |
| sd-22 | [Safe releases and database migrations](lessons/22-safe-releases-migrations.md) | [sd-05](lessons/05-indexes-query-plans.md), [sd-07](lessons/07-load-balancing-health.md), [sd-16](lessons/16-outbox-cdc.md), [sd-19](lessons/19-slos-error-budgets.md), [sd-20](lessons/20-logs-metrics-traces.md) | 40 |
| sd-23 | [Authentication, authorization, and tenant isolation](lessons/23-authentication-authorization-tenants.md) | [sd-02](lessons/02-http-api-design.md), [sd-08](lessons/08-caching-invalidation.md), [sd-09](lessons/09-connection-pooling.md) | 40 |
| sd-24 | [Backups, restore drills, and disaster recovery](lessons/24-backup-disaster-recovery.md) | [sd-06](lessons/06-requirements-capacity.md), [sd-11](lessons/11-object-storage-cdn.md), [sd-16](lessons/16-outbox-cdc.md), [sd-19](lessons/19-slos-error-budgets.md) | 40 |

Milestone: Define user-visible reliability, gather diagnostic evidence, release compatible changes, isolate tenants, and demonstrate recovery.

## 5. Advanced — Reason about guarantees

State the failure model and guarantee precisely, produce a counterexample to a weaker design, and defend where coordination is necessary.

| ID | Lesson | Prerequisites | Minutes |
|---|---|---|---|
| sd-25 | [Consistency models and execution histories](lessons/25-consistency-histories.md) | [sd-04](lessons/04-concurrency-basics.md), [sd-14](lessons/14-idempotency-deduplication.md), [sd-15](lessons/15-delivery-ordering.md), [sd-24](lessons/24-backup-disaster-recovery.md) | 45 |
| sd-26 | [Consensus, leader changes, and membership](lessons/26-consensus-membership.md) | [sd-13](lessons/13-timeouts-retries-jitter.md), [sd-15](lessons/15-delivery-ordering.md), [sd-25](lessons/25-consistency-histories.md) | 50 |
| sd-27 | [Distributed transactions and atomic commitment](lessons/27-distributed-transactions.md) | [sd-17](lessons/17-sagas-compensation.md), [sd-25](lessons/25-consistency-histories.md), [sd-26](lessons/26-consensus-membership.md) | 50 |
| sd-28 | [Clocks, leases, and fencing tokens](lessons/28-clocks-leases-fencing.md) | [sd-13](lessons/13-timeouts-retries-jitter.md), [sd-14](lessons/14-idempotency-deduplication.md), [sd-25](lessons/25-consistency-histories.md), [sd-26](lessons/26-consensus-membership.md) | 50 |
| sd-29 | [Multi-region replication and conflict resolution](lessons/29-multi-region-conflicts.md) | [sd-23](lessons/23-authentication-authorization-tenants.md), [sd-24](lessons/24-backup-disaster-recovery.md), [sd-25](lessons/25-consistency-histories.md), [sd-26](lessons/26-consensus-membership.md), [sd-28](lessons/28-clocks-leases-fencing.md) | 50 |
| sd-30 | [Stream processing, event time, and correctness](lessons/30-stream-processing-correctness.md) | [sd-15](lessons/15-delivery-ordering.md), [sd-16](lessons/16-outbox-cdc.md), [sd-20](lessons/20-logs-metrics-traces.md), [sd-25](lessons/25-consistency-histories.md) | 50 |

Milestone: State the failure model and guarantee precisely, produce a counterexample to a weaker design, and defend where coordination is necessary.

## Case-study entry points

Cases can be attempted as soon as their prerequisites are understood; their display order does not add hidden prerequisites.

| ID | Case | Prerequisites | Minutes |
|---|---|---|---|
| cs-01 | [Design a ticket-booking system](case-studies/01-ticket-booking.md) | [sd-04](lessons/04-concurrency-basics.md), [sd-05](lessons/05-indexes-query-plans.md), [sd-06](lessons/06-requirements-capacity.md), [sd-08](lessons/08-caching-invalidation.md), [sd-14](lessons/14-idempotency-deduplication.md), [sd-16](lessons/16-outbox-cdc.md), [sd-17](lessons/17-sagas-compensation.md), [sd-18](lessons/18-backpressure-load-shedding.md) | 75 |
| cs-02 | [Design a payment-processing workflow](case-studies/02-payment-processing.md) | [sd-14](lessons/14-idempotency-deduplication.md), [sd-15](lessons/15-delivery-ordering.md), [sd-16](lessons/16-outbox-cdc.md), [sd-17](lessons/17-sagas-compensation.md), [sd-19](lessons/19-slos-error-budgets.md), [sd-20](lessons/20-logs-metrics-traces.md), [sd-23](lessons/23-authentication-authorization-tenants.md), [sd-24](lessons/24-backup-disaster-recovery.md) | 90 |
| cs-03 | [Design a durable job scheduler](case-studies/03-job-scheduling.md) | [sd-09](lessons/09-connection-pooling.md), [sd-10](lessons/10-queues-background-jobs.md), [sd-14](lessons/14-idempotency-deduplication.md), [sd-16](lessons/16-outbox-cdc.md), [sd-18](lessons/18-backpressure-load-shedding.md), [sd-20](lessons/20-logs-metrics-traces.md), [sd-26](lessons/26-consensus-membership.md), [sd-28](lessons/28-clocks-leases-fencing.md) | 90 |
| cs-04 | [Design search and autocomplete](case-studies/04-search-autocomplete.md) | [sd-05](lessons/05-indexes-query-plans.md), [sd-08](lessons/08-caching-invalidation.md), [sd-12](lessons/12-pagination-access-patterns.md), [sd-15](lessons/15-delivery-ordering.md), [sd-16](lessons/16-outbox-cdc.md), [sd-18](lessons/18-backpressure-load-shedding.md) | 75 |
| cs-05 | [Design a feature-flag service](case-studies/05-feature-flags.md) | [sd-08](lessons/08-caching-invalidation.md), [sd-14](lessons/14-idempotency-deduplication.md), [sd-16](lessons/16-outbox-cdc.md), [sd-19](lessons/19-slos-error-budgets.md), [sd-20](lessons/20-logs-metrics-traces.md), [sd-22](lessons/22-safe-releases-migrations.md), [sd-23](lessons/23-authentication-authorization-tenants.md) | 75 |
| cs-06 | [Design a multi-region SaaS platform](case-studies/06-multi-region-saas.md) | [sd-19](lessons/19-slos-error-budgets.md), [sd-20](lessons/20-logs-metrics-traces.md), [sd-21](lessons/21-performance-load-testing.md), [sd-23](lessons/23-authentication-authorization-tenants.md), [sd-24](lessons/24-backup-disaster-recovery.md), [sd-25](lessons/25-consistency-histories.md), [sd-26](lessons/26-consensus-membership.md), [sd-28](lessons/28-clocks-leases-fencing.md), [sd-29](lessons/29-multi-region-conflicts.md) | 100 |

## How the website uses this curriculum

This curriculum is the website's system design content. `python manage.py seed_content` turns every lesson and case study into one chapter and concept, with the concept slug taken from the catalogue. Each stage is a dashboard topic, and its lessons unlock at an XP level: stage 1 at level 1, stage 2 at 2, stage 3 at 4, stage 4 at 6 and stage 5 at 8. The case studies share a Case Studies topic and unlock one level after the lessons of their own stage (5, 7 or 9). These levels gate access in the app; they are separate from the knowledge prerequisites above, which the lesson page lists as links.

Two compiled reference chapters (Python internals, OS file handling) sit alongside the curriculum as optional background. See the [integration guide](dashboard-integration.md) for how notes, questions and games map onto the app.

## Mastery and review

For lessons, explain the example, solve the practice task, and justify both answers. Revisit the exact prerequisite you needed instead of restarting the whole course. For cases, use the 20-point rubric: the suggested threshold is 16, with no violated core invariant. These are proposed self-assessment rules, not validated psychometric scores or existing XP logic.

A dashboard may recommend the earliest incomplete item whose prerequisites are complete. Completion records belong to the learner; they are not stored in this content catalogue. See the [integration guide](dashboard-integration.md).

