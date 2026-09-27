# Load balancing, health checks, and draining

ID: sd-07 | Stage 2: intermediate | Suggested study: 30 minutes

Prerequisites: sd-01, sd-03, sd-06

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Choose connection-level or request-level routing for a workload.
- Separate readiness, liveness, and startup checks.
- Describe how to remove an instance without abandoning requests.

## Intuition

A load balancer chooses where work goes. It can spread traffic, but it cannot manufacture spare capacity or make a broken dependency healthy. Good routing needs a useful definition of which instances can currently serve which requests.

## How it works

A transport-level balancer routes connections; an application-level proxy can use HTTP information such as host or path. Round robin is simple, while least-outstanding-request policies can help with uneven request durations. Kubernetes readiness determines whether a pod receives Service traffic; liveness can trigger container restarts; startup checks protect slow initialization. A service should become ready only after required initialization, and stop accepting new work before it shuts down.

Technical references: [Configure Liveness, Readiness and Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/).

## Worked example

Assume four instances each sustain 100 requests/s at the target latency and the service receives 240/s. Normal distribution is 60/s each. With one instance removed, the remaining three handle 80/s each; with two removed, each sees 120/s and exceeds the measured operating point. This arithmetic assumes balanced requests of similar cost. A long-lived connection carrying many requests can make connection counts a poor proxy for load.

## Trade-offs and failure modes

Sticky sessions can simplify state access but concentrate work and complicate failover. Externalizing session state introduces a shared dependency. A liveness probe that fails whenever the database is slow can restart every application server during a database incident. Deep readiness checks may also remove all instances at once; design them for the actual request classes and dependency behavior. Health checks detect conditions after some delay, so in-flight failures still happen.

## Practice

Design an instance shutdown timeline for requests that normally finish within five seconds but sometimes stream for minutes. Specify when readiness changes, when new requests stop, how long existing work may drain, and what the client sees if the drain deadline expires.

### Answer guidance

First withdraw readiness and allow for routing propagation while keeping the server alive. Stop admitting new work and track active requests. Let short requests finish within a bounded grace period. Define reconnection/resume behavior for long streams rather than waiting forever. Force termination only after the declared deadline; callers still need safe retry or resume semantics.

## Knowledge check

### 1. Should a database slowdown always fail application liveness?

No. Restarting healthy application processes may worsen a shared dependency incident.

### 2. Does equal connection count imply equal request load?

No. Connections can differ greatly in request count, duration, and resource cost.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Configure Liveness, Readiness and Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

