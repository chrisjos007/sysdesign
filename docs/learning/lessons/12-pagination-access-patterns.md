# Pagination and data access patterns

ID: sd-12 | Stage 2: intermediate | Suggested study: 35 minutes

Prerequisites: sd-02, sd-05, sd-06

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Compare offset pagination with keyset pagination.
- Define a total ordering and cursor contract.
- Explain why a cursor is not automatically a snapshot.

## Intuition

Pagination is a contract for continuing through a collection. A good page boundary remains understandable when new items arrive, rows disappear, or many items have the same timestamp. The access pattern should shape the index and cursor together.

## How it works

LIMIT without a deterministic ORDER BY does not define a repeatable page. Large OFFSET values can be expensive because skipped rows still need computation. Keyset pagination continues after the last ordered key. For descending (created_at, id), the next page can filter tuples smaller than the last tuple, using an appropriate index. A cursor should bind the position to filters, tenant scope, and sort version. Treat it as untrusted input; opaque encoding alone provides neither authorization nor tamper protection.

Technical references: [LIMIT and OFFSET](https://www.postgresql.org/docs/current/queries-limit.html); [Paginate Search Results](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/paginate-search-results).

## Worked example

A feed contains timestamps 10:03, 10:02, and 10:01. Page one returns the first two. A new 10:04 item arrives before page two. Offset 2 now starts at 10:02, repeating an item. A cursor after the unique pair for 10:02 continues with older entries. However, if an existing item's sort key changes, it can cross the boundary. Snapshot semantics require a separate design, such as a bounded snapshot token or a point-in-time search view.

## Trade-offs and failure modes

Offsets offer easy random page numbers and can be adequate for small, stable collections. Keysets suit continuous traversal but usually cannot jump directly to page 10,000. A unique tiebreaker prevents ambiguity; nullable keys and mixed sort directions need explicit handling. A stable cursor does not freeze membership, and deleted rows may disappear. Decide whether the product wants a live feed, a stable export, or approximate browsing.

## Practice

Design a cursor for tenant-scoped audit events sorted by created_at descending, then event_id descending. Describe its fields, server validation, index candidate, and what guarantee you offer if events can be deleted.

### Answer guidance

Bind the last timestamp and event ID to the tenant/filter/sort contract, using a signed token or server-side cursor state if tampering must be detected. Recheck authorization for every page. Consider an index beginning with tenant_id, created_at, event_id. Promise live traversal with possible deletions unless you also implement a retention-backed snapshot.

## Knowledge check

### 1. Why is created_at alone often an insufficient cursor key?

Several rows can share that value, so a unique tiebreaker is needed to continue without ambiguity.

### 2. Does keyset pagination guarantee an immutable result set?

No. It defines continuation; concurrent updates, deletions, and snapshot policy still determine visibility.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [LIMIT and OFFSET](https://www.postgresql.org/docs/current/queries-limit.html)
- [Paginate Search Results](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/paginate-search-results)

