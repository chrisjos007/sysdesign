# Delivery guarantees and ordering

ID: sd-15 | Level: Advanced | Stage 3: Handle distributed failures | Suggested study: 40 minutes

Prerequisites: sd-10, sd-14

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Trace the commit/acknowledgement ambiguity.
- State the boundary of an exactly-once claim.
- Choose ordering scope and handle repeated or stale events.

## Intuition

A message has several lives: it is published, stored, delivered, processed, and turned into an effect. Saying 'the queue guarantees delivery' leaves open which life is protected. Correctness comes from specifying the entire path and its failure assumptions.

## How it works

At-most-once processing avoids retries of uncertain deliveries but can lose work. At-least-once processing permits repetition so recovery can continue. Exactly-once processing is meaningful only within a defined protocol boundary. Kafka transactions can atomically combine Kafka output records and consumed offsets under the documented configuration; they do not automatically commit an unrelated database or send an email exactly once. Ordering is typically scoped to a partition or another ordered stream, not every message in the system.

Technical references: [Design: Message Delivery Semantics](https://kafka.apache.org/41/design/design/); [Consumer Acknowledgements and Publisher Confirms](https://www.rabbitmq.com/docs/confirms).

## Worked example

A consumer receives event e42, increments a SQL counter, and crashes before committing its broker offset. On restart it receives e42 again. Committing the offset first merely changes the failure to a potentially missing increment. One solution is a unique processed-event record and the counter change in the same SQL transaction. After a crash, replay sees e42 already applied. The broker can then advance independently because repeating that local transaction no longer repeats the effect.

## Trade-offs and failure modes

Global ordering reduces parallelism and requires coordination. Per-account ordering may be enough for account state while allowing different accounts to proceed independently. Multiple workers can finish jobs out of delivery order. Include entity versions or sequence numbers and define what consumers do with gaps or stale updates. A deduplication store must retain IDs long enough for the actual replay policy; forgetting them while old messages remain replayable breaks the guarantee.

## Practice

Events version 12 and version 11 update the same search document, but 12 arrives first. Compare a full-state replacement event with a delta event such as 'increment quantity by one.' Explain when rejecting older versions is safe.

### Answer guidance

For complete versioned state, rejecting version 11 after applying 12 can preserve the latest known projection. For independent deltas, discarding an earlier event may lose a required change; use ordered processing, gap recovery, or an operation model that safely composes. The payload semantics determine the rule, not the broker label.

## Knowledge check

### 1. Does transactional Kafka processing automatically make an external SQL update exactly once?

No. The external effect needs its own coordinated or idempotent commit strategy.

### 2. Can messages delivered in order produce effects out of order?

Yes. Concurrent workers, retries, and differing execution times can change completion order.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Design: Message Delivery Semantics](https://kafka.apache.org/41/design/design/)
- [Consumer Acknowledgements and Publisher Confirms](https://www.rabbitmq.com/docs/confirms)

