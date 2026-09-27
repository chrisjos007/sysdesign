# Object storage, delivery, and CDNs

ID: sd-11 | Stage 2: intermediate | Suggested study: 30 minutes

Prerequisites: sd-01, sd-02, sd-08

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Separate binary objects from transactional metadata.
- Design an upload and publish sequence.
- Explain why storage consistency and CDN freshness differ.

## Intuition

Large files are often better addressed as objects than stored inside application rows. The database can describe ownership and status while an object store holds bytes. A CDN places reusable responses near readers, adding a separate caching layer with its own freshness rules.

## How it works

An object store exposes objects through keys and metadata, often with multipart upload and access controls. Amazon S3 documents strong read-after-write consistency for object PUT and DELETE operations; this does not automatically refresh a downstream CDN or create a transaction with an application database. Immutable, versioned keys make content replacement explicit. The metadata can switch to a new object version after validation, while old cached URLs continue identifying the old bytes.

Technical references: [What Is Amazon S3?](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html); [RFC 9111: HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111).

## Worked example

For a 200 MB learning video, the application creates a pending upload record and grants a short-lived, scoped upload capability. The client transfers bytes directly to storage. A completion worker verifies the expected object, size/checksum policy, and processing result before publishing playable metadata. If the object upload succeeds but the metadata update fails, the user still sees pending; a reconciler can finish the transition or retire the orphan according to policy.

## Trade-offs and failure modes

Direct upload reduces application bandwidth but requires careful capability scope and post-upload validation. A CDN lowers origin traffic for reusable files, but cache misses and data transfer still cost resources. Private content needs access control at delivery time; an obscure object key is not permission. Keep unpublished uploads separate from public delivery. Retention and cleanup should account for retries, replacement versions, and partially completed uploads.

## Practice

A teacher replaces a worksheet at the same URL. Some students see the old version. Design a publish flow with predictable version identity and explain what happens if the database pointer switches before the new object is ready.

### Answer guidance

Upload and validate a new immutable key, then atomically update metadata to reference it. Serve the metadata with an appropriate freshness policy. If the pointer changes too early, readers can receive missing or invalid content; therefore publication follows object readiness. Garbage-collect older versions only after accounting for still-valid references and retention.

## Knowledge check

### 1. Does a strongly consistent object store guarantee fresh CDN responses?

No. The CDN can retain a previously fetched representation under its independent cache policy.

### 2. Why keep an upload record in a pending state?

It separates successful byte transfer from validation and publication, and makes incomplete workflows recoverable.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [What Is Amazon S3?](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html)
- [RFC 9111: HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111)

