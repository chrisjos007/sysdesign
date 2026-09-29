# HTTP and API design: define the contract

ID: sd-02 | Level: Beginner | Stage 1: Understand a request | Suggested study: 25 minutes

Prerequisites: sd-01

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Choose a method and response contract for a resource.
- Distinguish safe methods from idempotent operations.
- Use conditional updates to detect conflicting edits.

## Intuition

An API is a promise about what a caller may ask, what the server changes, and what a response means. A URL and JSON shape are only part of that promise. Good contracts also explain retries, validation failures, permissions, and whether work has actually finished.

## How it works

HTTP separates method semantics from representation formats. GET is safe: clients do not request a state-changing action. PUT and DELETE are idempotent in their intended effect, although repeated responses can differ. POST has no general idempotency guarantee. A 201 response describes creation; 202 means accepted for processing, not completed successfully. An ETag identifies a representation version. Combining If-Match with a state-changing request lets a server reject a stale precondition with 412. Cache and authorization behavior remain separate decisions.

Technical references: [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110).

## Worked example

For a teaching task API, POST /tasks with a stable request key returns 201 and a task ID when creation is durable. POST /exports returns 202 plus an operation URL because export generation is asynchronous. GET /operations/123 reports queued, running, succeeded, or failed. For editing a title, two clients read ETag v7. The first writes with If-Match v7 and produces v8; the second must refresh or resolve its edit after its stale condition fails.

## Trade-offs and failure modes

A synchronous result is convenient but consumes the caller's deadline. An asynchronous contract needs durable operation state, expiry rules, and an explicit failure surface. A full-resource PUT can overwrite fields a caller did not intend to change unless the contract is clear. Returning 200 for every outcome hides distinctions clients need for recovery. Automatic retries of POST are unsafe without an explicit deduplication contract.

## Practice

Specify a report-generation API: request fields, success response, status resource, three terminal/nonterminal states, and what happens when the caller submits the same operation twice. Explain how a caller distinguishes failed report creation from a temporarily unreachable status endpoint.

### Answer guidance

Use a stable operation ID with a defined idempotency scope, return 202 only after durable acceptance, and expose a readable status resource. A terminal failed state concerns the operation; a network error during status retrieval leaves its state unknown. Repeating the same key should retrieve the same accepted operation under the documented retention policy.

## Knowledge check

### 1. Can repeated DELETE requests be idempotent if the second returns 404?

Yes. Idempotence concerns intended state effects, not identical status codes.

### 2. Does 202 mean that the requested report exists?

No. It means processing was accepted; completion needs a separate observation.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110)

