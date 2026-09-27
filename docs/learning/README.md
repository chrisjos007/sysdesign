# System design learning library

A beginner-to-expert expansion for SysDesign Quest: **30 concept lessons, six design case studies, and 78 knowledge-check questions with answer explanations**. Research date: **27 September 2026**.

Start with the [curriculum map](curriculum-map.md). Open [lesson 1](lessons/01-dns-tcp-tls.md) if you are new to system design, or use prerequisites to enter at the appropriate point. The [case studies](#case-studies) turn the mechanisms into designs you can defend.

## What is saved

| File or folder | Purpose |
|---|---|
| [curriculum-map.md](curriculum-map.md) | Ordered path, prerequisites, milestones, and existing-content connections |
| [lessons/01-dns-tcp-tls.md](lessons/01-dns-tcp-tls.md) through lesson 30 | Explanations, examples, failure modes, practice, and answer guidance |
| [case-studies/01-ticket-booking.md](case-studies/01-ticket-booking.md) through case 6 | Requirements, estimates, APIs/data models, reference diagrams, recovery scenarios, and rubrics |
| [catalogue.json](catalogue.json) | Metadata, prerequisite IDs, knowledge checks, rubrics, and reference architecture data |
| [catalogue.schema.json](catalogue.schema.json) | JSON Schema for the catalogue contract |
| [sources.json](sources.json) | 55 primary-source references with review dates |
| [dashboard-integration.md](dashboard-integration.md) | Field meanings and mapping to the current website |
| [glossary.md](glossary.md) | Short definitions for recurring terms |

This package is the website's system design content. `python manage.py seed_content` reads it into lessons, quizzes and games, replacing the earlier book-derived chapters; see the [integration guide](dashboard-integration.md) for the mapping.

## How to study

1. Read the objectives and verify the prerequisites.
2. Explain the worked example in your own words, keeping units and assumptions visible.
3. Attempt the practice task before reading its answer guidance.
4. Answer all knowledge checks with a reason, then revisit the failure scenario.
5. For a case study, draw your own design before reading the reference architecture and score it using the rubric.

Suggested times include reading and exercises. They total **1635 minutes (about 27.3 hours)** for one pass; implementation labs and repetition are extra. These are planning estimates, not measured learner outcomes. Expert is a curriculum stage, not a certification of professional expertise.

## Case studies

- [Design a ticket-booking system](case-studies/01-ticket-booking.md) — Build a reservation workflow whose correctness survives double clicks, expired holds, payment delays, and heavy contention.
- [Design a payment-processing workflow](case-studies/02-payment-processing.md) — Design the application-side payment workflow around stable operation identity, durable state, and reconciliation.
- [Design a durable job scheduler](case-studies/03-job-scheduling.md) — Build a scheduler that can explain every accepted job through retries, stale workers, and leadership changes.
- [Design search and autocomplete](case-studies/04-search-autocomplete.md) — Design a search service that stays useful while its derived index lags, rebuilds, and handles repeated events.
- [Design a feature-flag service](case-studies/05-feature-flags.md) — Build a flag system whose rollout decisions remain predictable when configuration distribution fails.
- [Design a multi-region SaaS platform](case-studies/06-multi-region-saas.md) — Design regional operation and failover around a precise authority model, measurable recovery targets, and tenant isolation.

## Editorial and source policy

The explanations and teaching scenarios are original writing. Linked standards, official product documentation, papers, and first-party engineering material support the mechanisms; no book chapter text has been reproduced. Examples, capacity numbers, target latencies, architecture choices, and exercises are hypothetical unless explicitly stated otherwise.

Each lesson links its technical references; the registry records the review date. Live documentation URLs can change, and provider-specific behavior must be rechecked before implementation. Mechanisms and limitations are distinguished from the proposed choices in each case. Source references indicate provenance, not affiliation or endorsement.

The existing website's book-derived concepts are linked through their verified source-data slugs in the catalogue. They are background connections, not a claim that these new notes came from those books.
