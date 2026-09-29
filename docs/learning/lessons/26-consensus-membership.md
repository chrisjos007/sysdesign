# Consensus, leader changes, and membership

ID: sd-26 | Level: Advanced | Stage 5: Reason about guarantees | Suggested study: 50 minutes

Prerequisites: sd-13, sd-15, sd-25

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Separate consensus safety from progress.
- Explain quorum intersection and leader-log restrictions.
- Plan membership changes without creating competing majorities.

## Intuition

Consensus gives replicas a shared decision order despite some failures. It is not a promise that every replica is currently reachable, nor that every node may accept independent conflicting decisions. The hard part is preserving committed history while leadership and membership change.

## How it works

Raft uses terms, elections, a replicated log, and rules constraining which candidate can lead. A leader commits a current-term entry after replication to a majority under the applicable configuration; older entries are committed indirectly according to the protocol. Election/log restrictions preserve committed history. The extended paper's joint-consensus transition requires agreement from majorities of both old and new configurations. Learners are non-voting members that can catch up before promotion, avoiding a premature increase in the voting quorum.

Technical references: [In Search of an Understandable Consensus Algorithm (extended version)](https://raft.github.io/raft.pdf); [Raft Learner](https://etcd.io/docs/v3.6/learning/design-learner/).

## Worked example

Five voting members require three votes. A 3–2 partition permits the three-member side to make progress if it has an eligible leader; the two-member side cannot independently commit. Now imagine replacing membership {A,B,C} with {C,D,E} by changing nodes' settings independently. Old majority {A,B} and new majority {D,E} are disjoint. A supported reconfiguration protocol is necessary to prevent both from independently treating themselves as authoritative.

## Trade-offs and failure modes

More voters can improve failure tolerance but add replication and coordination costs. A slow learner needs bandwidth and snapshot capacity; promoting it before it catches up can reduce availability. A three-voter group tolerates one unavailable member, not every possible regional outage regardless of placement. Reads from a node that once was leader need a protocol to establish current authority or an explicitly weaker read contract. Consensus assumes a defined failure model; ordinary Raft is not Byzantine-fault tolerance.

## Practice

A three-voter cluster has one failed member and you want to add a replacement. Explain the risk of first adding an empty node as a fourth voter, and propose a safer supported procedure.

### Answer guidance

Moving from three voters to four raises the majority from two to three. With one old voter down and a new voter not ready, progress can be lost. Preserve the functioning quorum, use the implementation's supported learner/replacement workflow, wait for catch-up, and apply membership changes through the protocol. Do not manually invent a reconfiguration sequence from quorum arithmetic alone.

## Knowledge check

### 1. Does a timeout prove the leader is dead?

No. It may be slow or partitioned; elections and term rules must preserve safety despite false suspicions.

### 2. Why must membership changes be coordinated?

Independent old and new majorities can otherwise make conflicting decisions without intersecting.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [In Search of an Understandable Consensus Algorithm (extended version)](https://raft.github.io/raft.pdf)
- [Raft Learner](https://etcd.io/docs/v3.6/learning/design-learner/)

