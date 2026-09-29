# Backpressure, load shedding, and graceful degradation

ID: sd-18 | Level: Advanced | Stage 3: Handle distributed failures | Suggested study: 35 minutes

Prerequisites: sd-03, sd-07, sd-09, sd-10, sd-13

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Distinguish rate limits, concurrency limits, and queue bounds.
- Choose which work to reject or degrade under overload.
- Calculate how long a burst buffer takes to fill.

## Intuition

A system under overload needs a way to say 'less work' before it spends all its resources failing. Backpressure slows producers or limits consumption. Load shedding rejects some work. Graceful degradation reduces what a successful response attempts to do.

## How it works

Rate limits bound arrivals over time; concurrency limits bound in-flight work; queue limits bound waiting work. These controls address different resources. A service may have low request rate but high concurrency when calls become slow. Admission should occur before expensive work where possible, preserve essential capacity, and respect deadlines. Google's overload guidance discusses capacity-aware rejection and prioritization; the useful target is completed valuable work, not admitting every request.

Technical references: [Handling Overload](https://sre.google/sre-book/handling-overload/); [Control and Limit Retry Calls](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html).

## Worked example

Suppose arrivals reach 1,400 jobs/s while workers sustain 1,000/s. A 2,000-job buffer fills in roughly 2,000 / 400 = 5 seconds from empty. Adding a larger buffer changes how long failure is postponed; it does not remove the 400/s deficit. If jobs expire after three seconds, a deep queue may spend resources processing outcomes nobody can use. Admission and prioritization should reflect that usefulness deadline.

## Trade-offs and failure modes

Rejecting requests harms some users immediately but can prevent a collapse affecting everyone. Poor prioritization can starve low-priority tenants. A global limit can let one noisy tenant consume all capacity; per-tenant budgets with a shared ceiling give more control. Fallbacks need their own budget: switching every cache miss to SQL or every search failure to an expensive scan can amplify an incident. Retrying rejected work immediately defeats shedding.

## Practice

Design overload behavior for checkout, product recommendations, and analytics ingestion sharing a service. Specify reserved resources, bounded queues, client behavior, and the recovery signal that allows traffic to increase.

### Answer guidance

Give checkout an explicit capacity budget and protect its dependencies. Omit or simplify recommendations when their budget is exhausted. Buffer analytics only within a declared retention/age limit, then apply a documented sampling or rejection policy. Clients back off with jitter and a finite retry budget. Restore load gradually based on observed latency, queue age, errors, and resource saturation.

## Knowledge check

### 1. Can a requests-per-second limit alone protect a dependency whose latency suddenly increases tenfold?

Not reliably. In-flight work can grow dramatically, so concurrency and waiting also need bounds.

### 2. Why can a fallback make an outage worse?

The alternative path may be more expensive or have less capacity than the normal path.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Handling Overload](https://sre.google/sre-book/handling-overload/)
- [Control and Limit Retry Calls](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html)

