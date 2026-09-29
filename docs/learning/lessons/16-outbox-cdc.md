# Transactional outbox and change data capture

ID: sd-16 | Level: Advanced | Stage 3: Handle distributed failures | Suggested study: 40 minutes

Prerequisites: sd-05, sd-10, sd-14, sd-15

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Identify the failure gap in a database-plus-broker dual write.
- Design an atomic outbox record and replayable publication.
- Separate database changes from stable domain events.

## Intuition

An order update and its notification are often stored in different systems. Calling both systems in sequence creates a gap: either the order exists without the event, or the event exists for an order that did not commit. An outbox puts the intent to publish beside the business change.

## How it works

In one local database transaction, update business state and insert an outbox event. A relay later publishes committed events using polling or change data capture (CDC). CDC reads database changes, commonly from a durable change log. The outbox pattern makes the business write and publication intent atomic; publication can still repeat. Debezium's outbox router uses an event identifier and an aggregate key, helping consumers deduplicate and route related events to the appropriate ordered partition.

Technical references: [Outbox Event Router](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html).

## Worked example

Transaction T confirms order 81 and adds event e81 with aggregate_id 81, aggregate_version 3, type OrderConfirmed, schema_version 1, and the necessary payload. A relay publishes e81, then crashes before recording progress. Its restart may publish e81 again. The order is not lost, but consumers must handle the duplicate. If the broker is down for an hour, the database still contains publication intent; eventual delivery depends on retaining it and restoring a functioning relay.

## Trade-offs and failure modes

A raw row-change stream couples consumers to table layouts. Explicit domain events can provide a more stable business contract. Polling is simple but needs efficient indexing, ownership, and cleanup; CDC has connector, log-retention, and recovery concerns. Neither guarantees that independent relays preserve entity order without a designed ordering protocol. Treat outbox lag, disk growth, failed payloads, and replay as operational concerns.

## Practice

Design outbox cleanup for a relay that may be offline for six hours. Explain why deleting every row older than one hour is unsafe, and how you would recover if the CDC connector's required log position is no longer available.

### Answer guidance

Retention must cover delivery/replay guarantees and account for relay progress, with extra operational margin. Age alone does not prove publication. Preserve enough durable event state to republish or rebuild, monitor connector lag against retained logs, and define a controlled resnapshot/reconciliation process. A missing log segment cannot be wished away by restarting the connector.

## Knowledge check

### 1. Does the outbox remove duplicate event delivery?

No. It removes the local dual-write gap; relays can republish after uncertain outcomes.

### 2. Why store an event schema version?

Consumers need a stable way to interpret payloads as producers evolve independently.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Outbox Event Router](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html)

