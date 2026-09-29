# Caching, invalidation, and stampedes

ID: sd-08 | Level: Intermediate | Stage 2: Scale a service | Suggested study: 35 minutes

Prerequisites: sd-02, sd-03, sd-05

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Choose a cache key, freshness policy, and authority.
- Explain a stale refill race and a cache stampede.
- Estimate origin demand from hit rate and misses.

## Intuition

A cache keeps a reusable copy closer to the reader or cheaper to retrieve. Its value depends on reuse and how old the copy may become. Before selecting a cache product, identify which answer is authoritative and when a stale answer is unacceptable.

## How it works

In cache-aside, an application looks in the cache, reads the authority on a miss, and fills the cache. TTL limits a copy's lifetime but is not a complete consistency protocol. Eviction removes entries under capacity pressure; expiration concerns freshness. HTTP caching has distinct controls: no-cache requires validation before reuse, while no-store forbids storage by caches subject to the directive. Validators such as ETags can avoid transferring an unchanged representation. Request coalescing lets one request refresh a key while others wait or use an explicitly permitted stale value.

Technical references: [Caching Challenges and Strategies](https://aws.amazon.com/builders-library/caching-challenges-and-strategies/); [RFC 9111: HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111).

## Worked example

At 1,000 reads/s and a 95% hit rate, the origin receives roughly 50 cache-miss reads/s, ignoring refresh work. If a restart empties the cache, demand can rise toward 1,000/s. Suppose reader A fetches version 4, writer B commits version 5 and invalidates the cache, then A fills the cache with version 4. Invalidation happened, yet stale data returned. Version-aware fills or a carefully designed coherence protocol are needed when this race violates the contract.

## Trade-offs and failure modes

Long TTLs improve reuse but extend stale visibility. Short TTLs and synchronized expiry can create bursts. Randomized expiry, bounded refreshes, and prewarming address different failure modes. Cache keys must include tenant, authorization-relevant scope, and representation variants where applicable. Never let a shared cached answer bypass an access check. A cache outage needs a controlled fallback; sending every miss to an already saturated database is not a recovery plan.

## Practice

A product page may show stock up to 30 seconds old, but checkout must never sell unavailable stock. Design caching for both paths, including the behavior during a cache outage.

### Answer guidance

Cache the display with an explicit freshness policy and bounded refresh demand. Perform the inventory decision at the authoritative store with a conditional update or equivalent invariant enforcement. During cache failure, shed or degrade display work if the origin cannot absorb it; reserve capacity for authoritative checkout operations.

## Knowledge check

### 1. Does a 30-second TTL alone guarantee every served value is at most 30 seconds behind the authority?

No. Delayed fills, stale upstream reads, and refresh behavior can make the original data older than the entry's lifetime.

### 2. What does HTTP no-cache mean?

A stored response requires validation before reuse; it is not the same as no-store.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Caching Challenges and Strategies](https://aws.amazon.com/builders-library/caching-challenges-and-strategies/)
- [RFC 9111: HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111)

