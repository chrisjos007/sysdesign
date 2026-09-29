# Consistency models and execution histories

ID: sd-25 | Level: Advanced | Stage 5: Reason about guarantees | Suggested study: 45 minutes

Prerequisites: sd-04, sd-14, sd-15, sd-24

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Evaluate a history against a declared consistency model.
- Distinguish transaction isolation from real-time ordering.
- Explain which operations must stop during a partition.

## Intuition

Consistency is a rule about which observations are allowed. Calling a system 'strong' or 'eventual' without specifying operations and scope leaves the rule incomplete. A useful design argument starts with a short history of invocations, completions, and returned values.

## How it works

Linearizability makes each operation appear to take effect at one instant between invocation and completion, respecting real-time precedence. Serializability makes concurrent transactions equivalent to some serial order, without by itself requiring that order to follow real time. Strict serializability combines transaction serializability with real-time order. Read-your-writes and monotonic reads are session guarantees, not synonyms for global linearizability. Eventual convergence does not specify a finite freshness bound. During a network partition, linearizable operations cannot remain available on every separated side.

Technical references: [Linearizability](https://jepsen.io/consistency/models/linearizable); [Serializability](https://jepsen.io/consistency/models/serializable); [Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html).

## Worked example

A register starts at 0. A writes 1 and receives success at t2. B begins a read at t3, after t2, and receives 0. With no intervening write, that history violates linearizability. If B's read began before A's write completed, the operations overlap, and returning 0 may be legal by ordering the read before the write. Write down invocation and completion intervals rather than sorting events by client clock timestamps.

## Trade-offs and failure modes

Stronger guarantees may require coordination across replicas and may prevent progress when the required participants are unreachable. Weaker guarantees can serve more local operations but shift conflict/freshness handling to the application. Per-key linearizability does not automatically enforce a cross-key invariant such as 'every workspace keeps at least one owner.' A quorum arithmetic slogan alone does not prove a protocol linearizable; write ordering, version selection, and failure behavior matter.

## Practice

A shared workspace must always keep at least one owner. Its two owners each open the members page, see two owners listed, and each removes their own owner role at the same moment. State the invariant, show a bad interleaving, and identify why per-key atomic writes do not suffice. Offer one enforceable design.

### Answer guidance

The invariant is that the workspace keeps at least one owner. Both reads can precede either write, and each write changes a different membership row, so both succeed and the workspace is left with none. Use a transaction isolation/locking strategy that protects the shared predicate, or serialize the decision through one authoritative membership record with conditional versions. Validate that the chosen database actually rejects or coordinates the conflicting history.

## Knowledge check

### 1. Does serializability alone require a later transaction to reflect every earlier completed transaction in wall-clock order?

No. That real-time requirement belongs to strict serializability.

### 2. Can a stale read be legal when it overlaps a write?

Yes, under linearizability it may be ordered before that overlapping write; completed-before-started operations impose stronger constraints.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Linearizability](https://jepsen.io/consistency/models/linearizable)
- [Serializability](https://jepsen.io/consistency/models/serializable)
- [Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)

