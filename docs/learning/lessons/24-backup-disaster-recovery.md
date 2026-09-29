# Backups, restore drills, and disaster recovery

ID: sd-24 | Level: Advanced | Stage 4: Operate reliably | Suggested study: 40 minutes

Prerequisites: sd-06, sd-11, sd-16, sd-19

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Distinguish replication from recoverable backup history.
- Specify recovery point and recovery time objectives.
- Design a restore drill that verifies business invariants.

## Intuition

A replica can quickly copy an accidental deletion. A backup preserves a recoverable past, provided you can actually restore it. Recovery planning asks two different questions: how much recent data may be lost, and how long may recovery take?

## How it works

Recovery point objective (RPO) expresses tolerated data loss in time; recovery time objective (RTO) expresses tolerated restoration duration. PostgreSQL point-in-time recovery combines a base backup with the required continuous sequence of write-ahead logs. A logical dump is a different backup mechanism and is not interchangeable with a physical base backup for WAL replay. Recovery also depends on credentials, keys, configurations, software compatibility, and an operational procedure that can run during the failure.

Technical references: [Continuous Archiving and Point-in-Time Recovery](https://www.postgresql.org/docs/current/continuous-archiving.html).

## Worked example

Suppose corruption begins at 14:02. The latest verified base backup is from 02:00 and archived logs cover up to 14:05. A restore to a consistent point just before the damaging transaction may recover useful state, if all required logs exist. Restoring to the latest point would replay the corruption. If restore takes 45 minutes and verification/routing takes 20, observed recovery is at least 65 minutes, even if starting the replacement machine took only two.

## Trade-offs and failure modes

More frequent base backups cost storage and transfer but can reduce replay time. Replication improves failover speed without preserving every historical state. A backup in the same failure/credential domain may disappear with the original. Restoring one database can make it disagree with object storage, emitted events, or external providers. Reconcile these boundaries instead of assuming a database rollback reverses the world.

## Practice

Write a restore drill for a fictional learning service storing progress in SQL and submissions in object storage. Define the target time, verification checks, queue behavior, and the evidence you retain.

### Answer guidance

Restore into an isolated target, verify the backup/log chain, and measure each phase. Check representative progress totals and referenced object availability. Prevent uncontrolled workers from repeating external effects during validation. Reconcile outbox/events and submissions around the recovery point, then test application reads/writes and routing. Record achieved RPO/RTO and gaps; a successful backup job alone is not proof of recoverability.

## Knowledge check

### 1. Why is a current replica not a substitute for historical backups?

It may faithfully replicate destructive or corrupting changes.

### 2. What makes an RTO claim credible?

A timed, representative recovery exercise including data restoration, validation, dependencies, and traffic restoration.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Continuous Archiving and Point-in-Time Recovery](https://www.postgresql.org/docs/current/continuous-archiving.html)

