# Safe releases and database migrations

ID: sd-22 | Stage 4: production | Suggested study: 40 minutes

Prerequisites: sd-05, sd-07, sd-16, sd-19, sd-20

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Define a canary comparison and stop condition.
- Plan an expand-migrate-contract schema change.
- Identify what an application rollback cannot reverse.

## Intuition

During a rolling release, old and new application versions coexist. A safe change is therefore a compatibility exercise as much as a deployment exercise. The database, messages, and cached representations can outlive either version.

## How it works

A canary exposes a limited population to a change and compares meaningful signals against a control; duration, sample size, and traffic differences affect the evidence. For schema evolution, a useful design is expand, migrate, then contract: add compatible structures, move readers/writers with verification, and remove old structures only when unused. PostgreSQL documents operation-specific table locks and constraint validation behavior; 'online migration' is not a blanket guarantee that all DDL avoids blocking.

Technical references: [Canarying Releases](https://sre.google/workbook/canarying-releases/); [ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html).

## Worked example

Replace full_name with display_name. First add the new nullable column while old code still works. Deploy code that maintains both representations under a defined write rule. Backfill in small restartable batches, avoiding overwriting a newer display_name. Verify counts and semantics, switch reads, and observe. Remove old writes and the old column only after old application versions, jobs, and rollback paths no longer need them. The exact sequence changes if the transformation is lossy.

## Trade-offs and failure modes

A canary can miss a rare request type or tenant skew. A 1% rollout with little traffic may lack enough evidence for a high-reliability claim. Backfills compete with normal queries and replication; throttle them and track lag/locks. Rolling back application code does not undo an irreversible schema drop or already-published event. Prefer a forward repair when a rollback would interpret newer data incorrectly.

## Practice

Design a release that changes an event field from a string amount to integer minor units. Include consumer compatibility, historical replay, backfill, rollout signals, and the point after which rollback is unsafe.

### Answer guidance

Version the event contract and provide an explicit conversion with currency/precision rules. Upgrade consumers to understand both forms before producers emit the new form. Preserve handling of historical events and test replay. Canary relevant transaction outcomes, not just HTTP errors. Removing old readers or irreversibly converting data changes rollback options and must follow evidence that older components are gone.

## Knowledge check

### 1. Does deploying the previous application image reverse a database migration?

No. Data and schema changes persist independently and may no longer be compatible.

### 2. Why validate a backfill before dropping the old field?

Missing, stale, or incorrectly transformed values can otherwise become permanent user-visible data loss.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Canarying Releases](https://sre.google/workbook/canarying-releases/)
- [ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html)

