# Indexes and query plans: read less data

ID: sd-05 | Stage 1: beginner | Suggested study: 35 minutes

Prerequisites: sd-03, sd-04

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Derive an index candidate from filters and ordering.
- Read estimated versus actual plan information.
- Explain why an index can slow writes or be ignored.

## Intuition

An index is an alternate route to data, like a book's index of terms. It saves you from reading every page for a selective lookup, but maintaining the extra route costs storage and work each time relevant data changes.

## How it works

A query planner compares access strategies using statistics and estimated costs. A B-tree's leading columns influence which part of the index can be searched efficiently; the exact choices depend on the database and available optimizations. Filters, ordering, selectivity, and row width matter together. EXPLAIN shows a planned strategy. EXPLAIN ANALYZE executes the statement and reports measured behavior, so use a disposable environment for statements with effects. An index scan is not always better than a sequential scan.

Technical references: [Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html); [Multicolumn Indexes](https://www.postgresql.org/docs/current/indexes-multicolumn.html).

## Worked example

Suppose an orders table has 10 million rows. A common query filters tenant_id = 7 and status = 'open', sorts by created_at and id descending, and returns 20 rows. An index starting with (tenant_id, status, created_at, id) is a candidate. It groups the relevant equality filters before the ordered range, with id breaking timestamp ties. This does not prove it wins: compare plans and latency using representative data, including a large tenant and a tenant with few open orders.

## Trade-offs and failure modes

Every extra index adds write, storage, and maintenance costs. Covering indexes can reduce table reads at additional space cost. A low-selectivity query returning most of a table may favor scanning it. Stale statistics and skew can produce estimates that differ sharply from reality. An index also cannot fix an application issuing hundreds of avoidable queries per page.

## Practice

A dashboard fetches 50 projects and then issues one query per project for its owner. Identify the query-count problem. Propose a fetching strategy, and list what you would inspect before deciding to add an index.

### Answer guidance

The page performs 51 queries: an N+1 pattern. Fetch owners with a join or a bounded second query keyed by owner IDs, depending on the data model. Inspect total query count, actual row counts, filters, join keys, sorting, and measured plans. An index may help each lookup while leaving the avoidable round trips intact.

## Knowledge check

### 1. Why might a sequential scan be the right plan?

If a query needs much of the table, reading it sequentially can cost less than many index-guided table reads.

### 2. Is EXPLAIN ANALYZE a read-only inspection command for any SQL statement?

No. It executes the statement. Treat writes and side-effecting functions accordingly.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)
- [Multicolumn Indexes](https://www.postgresql.org/docs/current/indexes-multicolumn.html)

