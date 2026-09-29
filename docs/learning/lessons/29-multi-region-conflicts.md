# Multi-region replication and conflict resolution

ID: sd-29 | Level: Advanced | Stage 5: Reason about guarantees | Suggested study: 50 minutes

Prerequisites: sd-23, sd-24, sd-25, sd-26, sd-28

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Choose write ownership per invariant.
- Explain the loss hidden by last-writer-wins convergence.
- Apply a mergeable data type without claiming arbitrary invariant safety.

## Intuition

Putting data in several regions improves locality and recovery options, but also creates the question of who may decide a conflicting update. Design this per kind of data: a profile preference, a seat reservation, and a financial balance need different rules.

## How it works

A single write owner per entity avoids some concurrent-write conflicts but introduces routing and failover coordination. Asynchronous multi-writer replication needs reconciliation; last-writer-wins selects a winner rather than preserving every intent. CRDTs use carefully defined operations and merge rules to converge under stated assumptions; convergence does not automatically preserve arbitrary business constraints. Product modes matter: DynamoDB distinguishes multi-region eventual and strong consistency, with different replication and conflict behavior. Do not treat every 'global table' as the same model.

Technical references: [About CRDTs](https://crdt.tech/); [Conflict-free Replicated Data Types](https://arxiv.org/abs/1805.06358); [Using DynamoDB Global Tables](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-global-table-design.html).

## Worked example

Consider a grow-only counter with one durable component per region. Region A's state is {A:3,B:0}; B's state is {A:0,B:2}. Merging by component-wise maximum gives {A:3,B:2}, whose total is 5. Repeating that merge changes nothing. Each region may only increase its own component, and replica identity/state must survive recovery. This technique fits a count that only increases; it cannot by itself enforce a shared inventory maximum or safely implement decrements.

## Trade-offs and failure modes

Local writes reduce coordination latency but may require conflict resolution later. Cross-region coordination can enforce stronger rules while adding network delay and partition-related unavailability. Last-writer-wins can lose one user's edit even when replicas converge perfectly. Tombstones, replica retirement, metadata growth, and resynchronization matter for richer mergeable types. Data placement also affects operational and product constraints; document those as requirements instead of assuming every region may hold everything.

## Practice

A product wants globally editable display names and a final-seat reservation. Choose a conflict strategy for each and describe a regional partition.

### Answer guidance

For display names, a documented winner rule or user-visible conflict resolution may be acceptable. For the seat, route the invariant to one fenced authority or a coordination protocol; do not let both partitioned sides independently confirm it. The isolated side can offer pending/unavailable behavior. If the business instead allocates disjoint regional seat quotas, prove the allocation invariant and handle quota transfers through coordination.

## Knowledge check

### 1. Does eventual convergence mean no user update was lost?

No. A deterministic winner policy can converge after discarding a concurrent intent.

### 2. Can a CRDT counter alone guarantee never selling more than ten seats?

No. Independent increments may exceed the business limit; coordination or a proven allocation scheme is needed.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [About CRDTs](https://crdt.tech/)
- [Conflict-free Replicated Data Types](https://arxiv.org/abs/1805.06358)
- [Using DynamoDB Global Tables](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-global-table-design.html)

