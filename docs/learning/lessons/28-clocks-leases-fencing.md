# Clocks, leases, and fencing tokens

ID: sd-28 | Stage 5: expert | Suggested study: 50 minutes

Prerequisites: sd-13, sd-14, sd-25, sd-26

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Separate elapsed time, wall time, and causal ordering.
- Construct a stale lease-holder failure timeline.
- Place fencing checks at the resource that must be protected.

## Intuition

A lease says an owner is valid for a bounded period under a particular time model. It does not stop a paused process from waking up later and acting on an old belief. The resource receiving the write needs a way to reject obsolete authority.

## How it works

Wall clocks identify calendar time but can drift or jump. Monotonic clocks support local elapsed-time measurement; they do not establish a universal order across machines. Lamport clocks encode a relationship consistent with causal precedence, but a smaller logical timestamp alone does not prove one event caused another. Fencing associates ownership epochs with increasing tokens. A protected resource atomically rejects a write carrying an epoch older than its accepted authority. Lease expiry at a coordinator alone does not perform that downstream check.

Technical references: [Time, Clocks, and the Ordering of Events in a Distributed System](https://lamport.azurewebsites.net/pubs/time-clocks.pdf); [How to Do Distributed Locking](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html).

## Worked example

A thumbnail worker holds epoch 41 and stalls while processing an old source image. Its lease expires; another worker receives epoch 42 and publishes the new image. The old worker resumes with its epoch-41 result. If object publication only checks that the worker once acquired a lease, it can overwrite the newer output. Put the publication pointer in a store that atomically compares the current epoch and result update. The stale worker's conditional update must fail.

## Trade-offs and failure modes

Fencing works only where the destination enforces it. An email provider that ignores the token remains an external-effect problem. Checking the lease in a separate call and then writing creates another race. A simple highest-token-seen rule rejects old tokens after newer authority has been installed; it does not prove that an otherwise unseen expired lease is still valid. For strict expiry semantics, atomically validate current ownership/expiry at the authority used by the write.

## Practice

Design the conditional publication record for a worker pool. Include job ID, current owner epoch, result version, and the operation that changes it. Explain whether workers with the same epoch can safely repeat a write.

### Answer guidance

Store current_epoch and result metadata under a transactional or compare-and-set authority. Install new epochs through the ownership protocol, then allow a publication only when its epoch matches current_epoch and its result transition is valid. Same-epoch retries still require idempotency or version checks; fencing handles stale ownership, not every duplicate within one ownership period.

## Knowledge check

### 1. Does a distributed lock physically stop an expired worker?

No. The worker may continue; the protected resource must reject stale authority.

### 2. Does a monotonic clock order events on different machines?

No. Its useful guarantee concerns elapsed time within its local clock domain.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Time, Clocks, and the Ordering of Events in a Distributed System](https://lamport.azurewebsites.net/pubs/time-clocks.pdf)
- [How to Do Distributed Locking](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html)

