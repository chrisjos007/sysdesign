# Content-scout ledger

This file is the working memory for the content-scout agent (`.claude/agents/content-scout.md`). Each iteration reads it first and updates it last, on the `content-scout` branch. [catalogue.json](catalogue.json) is the record of what the curriculum covers. This file records what is planned, reviewed, rejected, or waiting on a decision.

## Next free IDs

- Lesson: sd-32, file `lessons/32-<slug>.md`
- Case study: cs-07, file `case-studies/07-<slug>.md`
- Catalogue `order`: 38

## Next review

sd-01

The rotation runs sd-01 to sd-31, then cs-01 to cs-06, then starts again at sd-01. All 37 items were first researched on 2026-09-27.

## Needs your decision

Put questions for the owner here: contradictory sources, changes that would reset learners' quiz attempts, or scope calls. Remove an item once it's answered.

- **Where should the Ring Balancer live?** `ring-balancer-cache-cluster` in `learn/management/commands/seed_games.py` is attached to `caching-invalidation` (sd-08) because no lesson covered consistent hashing when it was built. sd-31 (`partitioning-consistent-hashing`) now teaches the mechanism it plays. Moving it means changing its `concept` and its `source` line, which cites sd-08. `RingAttempt` rows point at the challenge, not the concept, so a reseed would keep learners' attempts, but the game would disappear from the sd-08 page. Its Challenge 2 also lands on sd-08's cache-stampede objective, so keeping it there is defensible. Left unchanged pending your call.

## Ideas queue

Highest value first. These are gaps found by searching the 36 current items on 2026-09-27, so confirm each one before writing. Stages and prerequisites are suggestions. A case study's stage must be advanced, production or expert.

1. **Rate limiting algorithms** (lesson, advanced). Token bucket, leaky bucket, fixed and sliding windows, distributed counters and their accuracy and cost trade-offs, 429 with Retry-After (RFC 6585, RFC 9110). sd-18 only mentions it in passing. Suggested prerequisites: sd-08, sd-13, sd-18.
2. **Replication and replication lag** (lesson, intermediate). Leader and follower, synchronous and asynchronous replication, read-your-writes and monotonic reads, and data loss on failover. It would bridge the beginner database lessons and sd-25. Suggested prerequisites: sd-03, sd-05, sd-31.
3. **Real-time delivery: polling, server-sent events and WebSockets** (lesson, intermediate). Connection cost, fan-out through a broker, and reconnect-and-resume. Suggested prerequisites: sd-01, sd-02, sd-07.
4. **Unique ID generation** (lesson, intermediate). Random UUIDs against time-ordered UUIDv7 (RFC 9562), Snowflake-style IDs, index locality, and clock rollback. sd-31 covers why ever-increasing keys hot-spot a range partition, so link to it rather than re-teach it. Suggested prerequisites: sd-05, sd-12, sd-31.
5. **Storage engines: B-trees and LSM-trees** (lesson, intermediate). Write-ahead logs, compaction, and read, write and space amplification. sd-05 touches B-trees only. Suggested prerequisites: sd-05.
6. **Secondary indexes on partitioned data** (lesson, intermediate). Local (per-partition) against global (separately partitioned) indexes, scatter-gather reads, and a global index that lags its table, such as DynamoDB's eventually consistent global secondary indexes. sd-31 stops at the partition key. Suggested prerequisites: sd-05, sd-31.
7. **Case study: URL shortener** (advanced). Key generation, redirect caching, click analytics, and abuse handling. Build idea 4 first; sd-31 covers partitioning.
8. **Case study: chat and messaging** (advanced). Per-conversation ordering, delivery and read receipts, and offline sync. Build idea 3 first.
9. **Case study: API rate limiter** (advanced). Build idea 1 first.
10. **Case study: news feed** (production). Fan-out on write against fan-out on read, very large accounts, and freshness. Build idea 2 first; sd-31 covers partitioning and hot keys.
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

### 2026-09-27 · extend · sd-31 Partitioning, hot keys, and consistent hashing
- Result: added lesson sd-31 (intermediate, 35 minutes, order 37, prerequisites sd-05, sd-06, sd-08). It covers range against hash partitioning, hot spots from ever-increasing keys, hash mod N remapping against consistent hashing with virtual nodes, fixed hash slots and stale routing, hot keys and write sharding, and the cost of rebalancing. Coverage check first: in `docs/learning`, "partition" appeared only as a network partition (sd-25, sd-26, sd-29, case studies) or a Kafka partition (sd-15, sd-16), and nothing covered consistent hashing. The catalogue item sits after sd-12 in file order because `test_stages_unlock_in_order` reads items in file order; its `order` is still 37. Game: matching challenge `match-partitioning`.
- Files: `docs/learning/lessons/31-partitioning-consistent-hashing.md` (new), `docs/learning/catalogue.json` (item, summary, content_version 2026-09-27.2), `docs/learning/sources.json` (7 sources), `docs/learning/curriculum-map.md`, `docs/learning/glossary.md` (6 terms), `docs/learning/README.md`, `docs/learning/dashboard-integration.md`, `docs/learning/content-ledger.md`, `learn/curriculum_questions.py` (6 questions), `learn/management/commands/seed_games.py`, `learn/management/commands/seed_content.py` (comment), `learn/test_curriculum.py` (36 to 37), `README.md`, `PRODUCT.md`, `CONTEXT.md` (new dated section; the older dated sections keep their historical counts).
- Sources checked: Karger et al., Consistent Hashing and Random Trees (STOC 1997; cited through MIT's PDF because the ACM DOI returns 403 to fetchers); DeCandia et al., Dynamo (SOSP 2007); Apache Cassandra 5.0 docs, Dynamo architecture page; Redis cluster specification; Google Cloud Bigtable schema design best practices (page updated 2026-09-24); CockroachDB hash-sharded indexes; DynamoDB write sharding. Read for confirmation but not cited: DynamoDB "Partitions and data distribution" and "Burst and adaptive capacity" (a single hot item is capped at one partition's 3,000 RCU and 1,000 WCU).
- Tests: passed (74 tests)
- Follow-ups: added idea "Secondary indexes on partitioned data" and pointed ideas 2, 4, 7 and 10 at sd-31. Raised the Ring Balancer's placement under Needs your decision.
