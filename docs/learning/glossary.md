# Learning glossary

Quick definitions for this curriculum. Each entry links to the full explanation, example, and primary references; definitions are scoped to the mechanisms taught here.

| Term | Meaning | Read more |
|---|---|---|
| Acknowledgement | A statement at a particular boundary that work was received or handled. Broker receipt, consumer handling, and business commit are different boundaries. | [Lesson 10](lessons/10-queues-background-jobs.md) |
| Admission control | Deciding whether to accept new work before it consumes constrained resources. | [Lesson 18](lessons/18-backpressure-load-shedding.md) |
| Atomicity | A group of changes taking effect together or not taking effect, within a specified transactional boundary. | [Lesson 27](lessons/27-distributed-transactions.md) |
| Authentication | Verifying an identity, such as the account associated with a session. | [Lesson 23](lessons/23-authentication-authorization-tenants.md) |
| Authorization | Deciding whether an identity may perform an action on a specific resource. | [Lesson 23](lessons/23-authentication-authorization-tenants.md) |
| Backpressure | A signal or limit that slows producers or consumers to match downstream capacity. | [Lesson 18](lessons/18-backpressure-load-shedding.md) |
| Cache stampede | Many requests concurrently fetching or rebuilding the same missing/expired cached data. | [Lesson 08](lessons/08-caching-invalidation.md) |
| CDC | Change data capture: observing committed database changes for downstream processing. | [Lesson 16](lessons/16-outbox-cdc.md) |
| CDN | Content delivery network: a distributed delivery/cache layer with behavior separate from the origin store. | [Lesson 11](lessons/11-object-storage-cdn.md) |
| Compensation | A new business action that addresses a prior action's consequences; it is not necessarily a perfect reversal. | [Lesson 17](lessons/17-sagas-compensation.md) |
| Concurrency | Multiple operations making progress over overlapping time intervals. | [Lesson 04](lessons/04-concurrency-basics.md) |
| Consensus | A protocol for replicas to agree on decisions under a stated failure model. | [Lesson 26](lessons/26-consensus-membership.md) |
| Consistent hashing | Placing keys and nodes on one hash ring so that a membership change moves only the keys on the affected arcs. | [Lesson 31](lessons/31-partitioning-consistent-hashing.md) |
| CRDT | A replicated data type with defined operations and merge rules designed to converge under specified assumptions. | [Lesson 29](lessons/29-multi-region-conflicts.md) |
| Cursor | A continuation token binding a page position to an ordering and query contract. | [Lesson 12](lessons/12-pagination-access-patterns.md) |
| Deadline | The total point beyond which an operation's caller no longer intends to wait. | [Lesson 13](lessons/13-timeouts-retries-jitter.md) |
| Deduplication | Recognizing previously seen operation/event identities to suppress repeated processing or effects. | [Lesson 14](lessons/14-idempotency-deduplication.md) |
| Durability | Persistence of an acknowledged result under the storage system's specified failures. | [Lesson 24](lessons/24-backup-disaster-recovery.md) |
| Error budget | The allowed amount of bad behavior implied by a defined service objective and measurement window. | [Lesson 19](lessons/19-slos-error-budgets.md) |
| ETag | An HTTP representation validator that can participate in cache validation or conditional updates. | [Lesson 02](lessons/02-http-api-design.md) |
| Event time | The time attributed to when an event occurred, distinct from when it was processed. | [Lesson 30](lessons/30-stream-processing-correctness.md) |
| Fencing token | An ownership epoch checked at the protected resource to reject obsolete authority. | [Lesson 28](lessons/28-clocks-leases-fencing.md) |
| Hash partitioning | Assigning each key to a partition by a hash of its value; it spreads sequential keys but loses sort order across partitions. | [Lesson 31](lessons/31-partitioning-consistent-hashing.md) |
| Hot key | A single key whose traffic overloads the one partition that owns it; rebalancing cannot split it. | [Lesson 31](lessons/31-partitioning-consistent-hashing.md) |
| Idempotency | Repeating the same logical operation has no additional intended effect under its documented scope and retention. | [Lesson 14](lessons/14-idempotency-deduplication.md) |
| Invariant | A rule that must remain true through every allowed state transition, including failures. | [Lesson 25](lessons/25-consistency-histories.md) |
| Isolation | The rules governing how concurrently executing transactions may observe and affect each other. | [Lesson 25](lessons/25-consistency-histories.md) |
| Jitter | Random variation in retry timing that reduces synchronized bursts. | [Lesson 13](lessons/13-timeouts-retries-jitter.md) |
| Lease | Time-bounded ownership under a declared clock/protocol model; it does not physically stop an old owner. | [Lesson 28](lessons/28-clocks-leases-fencing.md) |
| Linearizability | Operations behave as if each took effect at one instant within its execution interval, respecting real-time precedence. | [Lesson 25](lessons/25-consistency-histories.md) |
| Little's Law | L = lambda × W for stable, consistently measured averages: work in system equals throughput times time in system. | [Lesson 03](lessons/03-latency-throughput.md) |
| Load shedding | Deliberately rejecting selected work to preserve useful service under overload. | [Lesson 18](lessons/18-backpressure-load-shedding.md) |
| Outbox | Durable publication intent written in the same local transaction as the related business change. | [Lesson 16](lessons/16-outbox-cdc.md) |
| p95 / p99 | Latency percentiles describing distribution positions; sample size and computation convention matter. | [Lesson 03](lessons/03-latency-throughput.md) |
| Parallelism | Simultaneous execution of work, as distinct from merely overlapping progress. | [Lesson 04](lessons/04-concurrency-basics.md) |
| Partition | A communication separation in a distributed system; in data modeling, the same word can instead mean a data subset. | [Lesson 25](lessons/25-consistency-histories.md) |
| PITR | Point-in-time recovery: restoring data to a selected historical point using an appropriate backup/log chain. | [Lesson 24](lessons/24-backup-disaster-recovery.md) |
| Processing time | The time at which a stream processor handles an event. | [Lesson 30](lessons/30-stream-processing-correctness.md) |
| Projection | A derived representation built for a particular read pattern and recoverable from authoritative data. | [Lesson 16](lessons/16-outbox-cdc.md) |
| Quorum | A required set or count of participants whose agreement a protocol uses; arithmetic alone does not establish correctness. | [Lesson 26](lessons/26-consensus-membership.md) |
| Range partitioning | Assigning each partition a contiguous span of sorted keys, which keeps range scans local but concentrates writes of ever-increasing keys. | [Lesson 31](lessons/31-partitioning-consistent-hashing.md) |
| Readiness | Whether an instance is currently suitable to receive the traffic covered by its readiness contract. | [Lesson 07](lessons/07-load-balancing-health.md) |
| Rebalancing | Moving partitions or key ranges between nodes after a membership or load change; the copy costs network, disk, and time. | [Lesson 31](lessons/31-partitioning-consistent-hashing.md) |
| Reconciliation | Comparing independently recorded outcomes and resolving missing, inconsistent, or uncertain state. | [Lesson 17](lessons/17-sagas-compensation.md) |
| RPO | Recovery point objective: tolerated loss of recent data, expressed in time. | [Lesson 24](lessons/24-backup-disaster-recovery.md) |
| RTO | Recovery time objective: tolerated duration to restore the specified service. | [Lesson 24](lessons/24-backup-disaster-recovery.md) |
| Saga | A durable workflow of local commits with retry and compensation policies. | [Lesson 17](lessons/17-sagas-compensation.md) |
| Serializability | Concurrent transactions have an effect equivalent to some serial execution; real-time ordering is an additional property. | [Lesson 25](lessons/25-consistency-histories.md) |
| SLI / SLO | A service-level indicator measures behavior; a service-level objective gives its target and window. | [Lesson 19](lessons/19-slos-error-budgets.md) |
| Tail latency | The slow end of a latency distribution, where a minority of requests may experience much worse service. | [Lesson 03](lessons/03-latency-throughput.md) |
| Tenant | A customer or organizational isolation scope in a shared service. | [Lesson 23](lessons/23-authentication-authorization-tenants.md) |
| Throughput | Completed work per unit time, distinct from arrivals and individual response latency. | [Lesson 03](lessons/03-latency-throughput.md) |
| Tombstone | A durable deletion marker that can prevent older replicated or replayed data from resurrecting a record. | [Lesson 29](lessons/29-multi-region-conflicts.md) |
| TTL | Time to live: an expiry policy for a cached item or record, not a general consistency guarantee. | [Lesson 08](lessons/08-caching-invalidation.md) |
| Virtual node | One of many ring positions held by a physical node, used to even out load and to weight nodes by capacity. | [Lesson 31](lessons/31-partitioning-consistent-hashing.md) |
| Watermark | A stream processor's event-time progress signal used with a declared late-data policy. | [Lesson 30](lessons/30-stream-processing-correctness.md) |

