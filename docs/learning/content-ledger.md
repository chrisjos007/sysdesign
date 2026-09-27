# Content-scout ledger

This file is the working memory for the content-scout agent (`.claude/agents/content-scout.md`). Each iteration reads it first and updates it last, on the `content-scout` branch. [catalogue.json](catalogue.json) is the record of what the curriculum covers. This file records what is planned, reviewed, rejected, or waiting on a decision.

## Next free IDs

- Lesson: sd-31, file `lessons/31-<slug>.md`
- Case study: cs-07, file `case-studies/07-<slug>.md`
- Catalogue `order`: 37

## Next review

sd-01

The rotation runs sd-01 to sd-30, then cs-01 to cs-06, then starts again at sd-01. All 36 items were first researched on 2026-09-27.

## Needs your decision

Put questions for the owner here: contradictory sources, changes that would reset learners' quiz attempts, or scope calls. Remove an item once it's answered.

_Nothing open._

## Ideas queue

Highest value first. These are gaps found by searching the 36 current items on 2026-09-27, so confirm each one before writing. Stages and prerequisites are suggestions. A case study's stage must be advanced, production or expert.

1. **Partitioning and consistent hashing** (lesson, intermediate). Hash and range partitioning, hot keys, rebalancing, and consistent hashing with virtual nodes. The Ring Balancer game already teaches this, but it hangs off sd-08 because no lesson covers it. Suggested prerequisites: sd-05, sd-06, sd-08.
2. **Rate limiting algorithms** (lesson, advanced). Token bucket, leaky bucket, fixed and sliding windows, distributed counters and their accuracy and cost trade-offs, 429 with Retry-After (RFC 6585, RFC 9110). sd-18 only mentions it in passing. Suggested prerequisites: sd-08, sd-13, sd-18.
3. **Replication and replication lag** (lesson, intermediate). Leader and follower, synchronous and asynchronous replication, read-your-writes and monotonic reads, and data loss on failover. It would bridge the beginner database lessons and sd-25. Suggested prerequisites: sd-03, sd-05.
4. **Real-time delivery: polling, server-sent events and WebSockets** (lesson, intermediate). Connection cost, fan-out through a broker, and reconnect-and-resume. Suggested prerequisites: sd-01, sd-02, sd-07.
5. **Unique ID generation** (lesson, intermediate). Random UUIDs against time-ordered UUIDv7 (RFC 9562), Snowflake-style IDs, index locality, and clock rollback. Suggested prerequisites: sd-05, sd-12.
6. **Storage engines: B-trees and LSM-trees** (lesson, intermediate). Write-ahead logs, compaction, and read, write and space amplification. sd-05 touches B-trees only. Suggested prerequisites: sd-05.
7. **Case study: URL shortener** (advanced). Key generation, redirect caching, click analytics, and abuse handling. Build ideas 5 and 1 first.
8. **Case study: chat and messaging** (advanced). Per-conversation ordering, delivery and read receipts, and offline sync. Build idea 4 first.
9. **Case study: API rate limiter** (advanced). Build idea 2 first.
10. **Case study: news feed** (production). Fan-out on write against fan-out on read, very large accounts, and freshness. Build ideas 1 and 3 first.
11. **Probabilistic data structures** (lesson, advanced). Bloom filters, HyperLogLog and count-min sketch, with the false-positive arithmetic. Suggested prerequisites: sd-06, sd-08.
12. **Secrets, encryption at rest and key management** (lesson, production). Suggested prerequisites: sd-23, sd-24.

## Rejected

Ideas dropped after research, each with its reason, so they don't come back.

_None yet._

## How to log a run

Add an entry at the top of the Run log:

```
### YYYY-MM-DD · review|extend · <id> <title>
- Result: what changed, or "no change needed" and why
- Files: every file touched
- Sources checked: titles or URLs
- Tests: passed (N tests), or failed and stashed as "<stash message>"
- Follow-ups: ideas added to the queue, or items raised under Needs your decision
```

Then update Next free IDs, Next review, the Ideas queue (remove what you built and add what you found), Rejected and Needs your decision.

## Run log

_No runs yet._
