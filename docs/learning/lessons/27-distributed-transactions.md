# Distributed transactions and atomic commitment

ID: sd-27 | Level: Advanced | Stage 5: Reason about guarantees | Suggested study: 50 minutes

Prerequisites: sd-17, sd-25, sd-26

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Trace prepare and decision phases of atomic commitment.
- Explain the blocking risk of an uncertain prepared participant.
- Separate atomic commit from isolation and consensus.

## Intuition

A transaction spanning multiple authorities needs agreement about its outcome. Local commits cannot be undone merely because another service later fails. Atomic commitment asks participants to preserve a common commit-or-abort decision through crashes and recovery.

## How it works

In two-phase commit, a coordinator first asks participants to prepare. A prepared participant durably records enough state to finish later and promises not to choose an outcome independently. If all required votes permit it, the coordinator durably records commit before announcing it; otherwise it decides abort under the protocol. PostgreSQL PREPARE TRANSACTION supports participation in an externally managed protocol and retains locks while prepared. A participant uncertain of the decision may block until it can recover that decision. Atomicity does not itself define transaction isolation.

Technical references: [PREPARE TRANSACTION](https://www.postgresql.org/docs/current/sql-prepare-transaction.html).

## Worked example

A fictional transfer debits account X at store A and credits account Y at store B. Both participants prepare. The coordinator records commit, sends it to A, and crashes before notifying B. A has committed; B cannot safely abort just because its wait timer expired. Recovery must obtain the durable commit decision and complete B. If no durable commit decision exists, the coordinator's recovery rules determine an outcome without contradicting any already-announced decision.

## Trade-offs and failure modes

Prepared transactions retain resources and can block ordinary work. Replicating coordinator state can improve its availability, but does not remove the need for participants and recovery. Sagas accept visible intermediate states and compensation; they are appropriate for some business workflows but do not deliver the same semantics as atomic commitment. Often the simplest correct approach is to keep tightly coupled invariants inside one transactional authority.

## Practice

Compare three designs for moving credits between two balances: one database transaction, two-phase commit across stores, and a saga. State which intermediate states outsiders may observe and what happens when the second step is unreachable.

### Answer guidance

One local transaction can protect both balances if they fit one authority and appropriate isolation. Two-phase commit can coordinate all-or-nothing commitment but may leave participants prepared during unavailability; isolation still needs specification. A saga can expose a debit before the credit and must represent pending/compensating states. Select based on the invariant and availability needs, not on a preference for microservices.

## Knowledge check

### 1. Can a prepared participant safely abort solely because its timer expired?

Not if a commit decision may already exist; it must follow the protocol's recovery rules.

### 2. Does consensus automatically turn arbitrary database writes into a distributed transaction?

No. Consensus orders agreed state; atomic commitment and isolation across participants require additional protocol design.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [PREPARE TRANSACTION](https://www.postgresql.org/docs/current/sql-prepare-transaction.html)

