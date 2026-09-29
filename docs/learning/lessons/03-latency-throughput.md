# Latency, throughput, and queueing

ID: sd-03 | Level: Beginner | Stage 1: Understand a request | Suggested study: 30 minutes

Prerequisites: sd-01

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Separate response time, service time, arrival rate, and completion rate.
- Calculate average in-flight work using Little's Law.
- Recognize when averages conceal slow user experiences.

## Intuition

A restaurant can serve many meals per hour while making each customer wait a long time. Similarly, throughput counts completed work per unit time, while latency measures an individual operation's elapsed time. Increasing one does not automatically improve the other.

## How it works

End-to-end latency includes network travel, queue waiting, execution, and response transfer. Service time is only the time a resource spends doing work. For a stable system with consistent boundaries, Little's Law is L = lambda × W: average work in the system equals average throughput times average time in the system. It is not a formula for p99 latency or an assurance of stability. Tail percentiles describe slow requests; the mean can hide a small but painful slow population.

Technical references: [Queueing: Little's Law, lecture 8](https://ocw.mit.edu/courses/15-760a-operations-management-spring-2002/e6c66bef8fc37c9f4928ea8f816895ab_lecture8_feb22.pdf); [Service Level Objectives](https://sre.google/sre-book/service-level-objectives/).

## Worked example

At a steady 200 requests/s and mean response time of 0.15 s, average in-flight work is 30 requests. If response time becomes 0.6 s while throughput remains 200/s, average in-flight work becomes 120. That extra work may occupy memory or sockets even with little CPU usage. Separately, 990 requests at 20 ms and 10 at 2,000 ms have a 39.8 ms mean. The mean obscures the ten severe delays; percentile values also depend on the calculation convention and sample size.

## Trade-offs and failure modes

Batching can improve throughput by amortizing overhead but adds waiting before work begins. Parallel fan-out reduces serial work yet makes the slowest required branch important. A longer queue absorbs a brief burst but cannot fix sustained arrivals above processing capacity. Report offered traffic, completed traffic, errors, and latency together; dropping slow requests can make success-only latency appear better.

## Practice

A worker group receives 120 jobs/s and completes at most 100/s for five minutes, starting empty. Estimate the backlog. Then arrivals fall to 80/s. Estimate drain time at the same completion capacity. State the simplifying assumptions.

### Answer guidance

Backlog grows by 20 × 300 = 6,000 jobs. Spare capacity after the burst is 100 - 80 = 20 jobs/s, so clearing the backlog takes another 300 seconds. This fluid estimate assumes fixed capacity, no failures or retries, and similar job costs. It does not predict individual waiting-time percentiles.

## Knowledge check

### 1. At 50 requests/s and 0.2 s mean latency, what is average concurrency?

10 requests, if the measured system is stable and the throughput and latency refer to the same boundary.

### 2. Why can CPU be low while requests time out?

Requests may be waiting on locks, connections, network responses, or queues instead of consuming CPU.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Queueing: Little's Law, lecture 8](https://ocw.mit.edu/courses/15-760a-operations-management-spring-2002/e6c66bef8fc37c9f4928ea8f816895ab_lecture8_feb22.pdf)
- [Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)

