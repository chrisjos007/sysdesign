# Logs, metrics, traces, and useful observability

ID: sd-20 | Stage 4: production | Suggested study: 35 minutes

Prerequisites: sd-07, sd-10, sd-19

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Choose signals that answer a concrete debugging question.
- Propagate correlation across synchronous and queued work.
- Control metric cardinality and telemetry sensitivity.

## Intuition

Observability means having evidence to explain behavior you did not predict in advance. Start with a question: which users are failing, where is time spent, or which dependency changed? Recording everything without a question can make failures harder to find.

## How it works

OpenTelemetry describes metrics, logs, and traces as distinct signals. Metrics summarize measurements; logs record events; traces connect timed operations across a request. W3C Trace Context specifies interoperable trace identifiers and propagation headers. Application instrumentation must preserve context when crossing service and messaging boundaries. Trace relationships express execution structure, while durable business IDs identify an operation across retries, reconciliation, or days of processing.

Technical references: [Signals](https://opentelemetry.io/docs/concepts/signals/); [Trace Context](https://www.w3.org/TR/trace-context/).

## Worked example

An export takes 90 seconds. Its HTTP acceptance span lasts 70 ms, the queue wait is 85 seconds, and the worker takes 4.93 seconds. A web-server latency chart looks healthy while the user waits. Track acceptance latency, queue age, processing latency, and end-to-end completion separately. Include the operation ID in structured logs and link asynchronous work into the trace where the instrumentation supports it.

## Trade-offs and failure modes

Putting user_id, operation_id, or an arbitrary URL into metric labels can create enormous numbers of series. Prefer bounded labels such as route templates and outcome classes, and use logs/traces for detailed identifiers. Sampling reduces telemetry cost but can hide rare failures; design a strategy for error and slow-path visibility. Avoid secrets and unnecessary personal data in propagated context. An unavailable telemetry backend should not block the business request indefinitely.

## Practice

Design telemetry for a retrying notification worker. Specify three metrics, one structured log event, and a trace relationship. Explain how you would distinguish provider throttling from worker starvation.

### Answer guidance

Measure queue age, attempts by outcome, and completion latency, with bounded dimensions. Log an attempt's operation ID, provider response class, retry decision, and duration. Link the worker attempt to the accepted job or prior attempt. Rising queue age with idle workers suggests scheduling/consumption trouble; active attempts receiving throttle responses point toward provider limits. Validate these hypotheses with worker and dependency signals.

## Knowledge check

### 1. Why should request IDs usually not be metric labels?

Their near-unbounded values multiply time series and storage cost; logs or traces are better suited to individual IDs.

### 2. Does a fast acceptance endpoint prove a background workflow is fast?

No. Queue waiting and execution can dominate end-to-end latency after acceptance.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Signals](https://opentelemetry.io/docs/concepts/signals/)
- [Trace Context](https://www.w3.org/TR/trace-context/)

