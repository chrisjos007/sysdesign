# DNS, TCP, and TLS: follow a request

ID: sd-01 | Stage 1: beginner | Suggested study: 25 minutes

Prerequisites: None; start here.

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Trace a new HTTPS connection from name lookup to response.
- Separate name resolution, transport reliability, and transport security.
- Explain why a network timeout does not prove an operation failed.

## Intuition

Opening a website resembles finding an office, establishing a conversation, and checking whom you are speaking to. These are separate jobs. DNS maps names to records; a transport carries bytes; TLS protects a connection. A failure in any one can look like a page that never loads.

## How it works

A resolver answers a DNS query from cache or follows the DNS hierarchy toward authoritative servers. Cached answers have a time to live (TTL); a record change is not an instantaneous traffic switch. TCP provides an ordered byte stream, retransmission, and flow/congestion control. It does not define application messages or confirm database commits. TLS 1.3 authenticates the server in ordinary HTTPS deployments and negotiates keys for confidentiality and integrity; client certificates are optional. Certificate validation includes the requested name and trust chain. HTTP/1.1 and HTTP/2 commonly use TLS over TCP; HTTP/3 uses QUIC, so do not draw TCP underneath every HTTP request.

Technical references: [RFC 1034: Domain names — concepts and facilities](https://www.rfc-editor.org/rfc/rfc1034); [RFC 9293: Transmission Control Protocol](https://www.rfc-editor.org/rfc/rfc9293.html); [RFC 8446: TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446); [RFC 9114: HTTP/3](https://www.rfc-editor.org/rfc/rfc9114).

## Worked example

Assume a cold HTTP/2 connection takes 20 ms for DNS, 40 ms for TCP setup, 40 ms for TLS, and 90 ms for request delivery, server work, and response delivery. The illustrative total is 190 ms. Reusing a valid established connection removes the first three setup costs from this simplified request. This is a model, not a universal latency table: connection reuse, session resumption, packet loss, and geography change the result.

## Trade-offs and failure modes

Short DNS TTLs can improve responsiveness to routing changes while increasing lookup traffic; clients and existing connections still complicate failover. TLS termination at a proxy means the next network hop needs its own security decision. If the server commits an order and the response packet is lost, TCP cannot tell the client whether the business operation happened. Retrying safely requires an application contract.

## Practice

Draw two timelines for an order submission: one where the request never reaches the server and one where the server commits but the response never reaches the client. Mark the last event each participant can observe. Then identify which setup steps a second request can reuse.

### Answer guidance

Both timelines can end in the same client timeout. Only server-side state or a stable operation identifier can resolve the ambiguity. The second request may reuse the DNS answer and established transport/TLS connection, provided they remain valid. DNS cache reuse alone does not reuse an existing connection.

## Knowledge check

### 1. Does a TCP acknowledgement prove an order was saved?

No. It acknowledges transport receipt, not successful application processing or durable commit.

### 2. Why can users reach the old server after a DNS update?

Cached records and established connections may continue using the old destination; changing authoritative DNS does not revoke them.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [RFC 1034: Domain names — concepts and facilities](https://www.rfc-editor.org/rfc/rfc1034)
- [RFC 9293: Transmission Control Protocol](https://www.rfc-editor.org/rfc/rfc9293.html)
- [RFC 8446: TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446)
- [RFC 9114: HTTP/3](https://www.rfc-editor.org/rfc/rfc9114)

