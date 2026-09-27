# Sagas and compensating actions

ID: sd-17 | Stage 3: advanced | Suggested study: 40 minutes

Prerequisites: sd-14, sd-15, sd-16

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Model a workflow as durable local transitions.
- Separate compensation from transaction rollback.
- Handle timeout, retry, and manual-repair states explicitly.

## Intuition

A workflow spanning independently owned services rarely fits into one local transaction. A saga records a sequence of local commits and the business actions used when the overall workflow cannot finish. The intermediate states are real and can be visible.

## How it works

An orchestrated saga has a coordinator that tracks steps and commands participants. Choreography lets services react to events without one central workflow controller. Compensation is a new business action, not erasure of history: refunding a charge differs from pretending no charge occurred. AWS's saga guidance describes forward recovery through retries and backward recovery through compensation, with coordination and isolation challenges. Durable state, idempotent commands, and explicit recovery paths are necessary.

Technical references: [Saga Orchestration Pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html).

## Worked example

A fictional equipment-rental workflow reserves a bicycle, authorizes payment, and confirms the booking. If payment is declined, it releases the reservation. If payment succeeded but confirmation cannot be completed, it may void the authorization or issue a refund according to the provider state. A delayed success must not confirm a booking already canceled by a newer transition. Every step carries a workflow ID, step ID, and expected state/version.

## Trade-offs and failure modes

Orchestration makes progress and repair easier to inspect but creates a coordinator service to operate. Choreography reduces direct coordination while making global behavior harder to understand as participants grow. A saga usually does not provide transaction isolation: another workflow may observe reserved inventory before final confirmation. Compensation can fail or be impossible, so include retry limits, escalation, and an operator-visible repair state.

## Practice

An order is in payment_pending when the provider times out. The inventory hold expires while payment success arrives late. Define the allowable transitions and the action if inventory can no longer be reserved.

### Answer guidance

Do not translate timeout directly into declined. Reconcile the provider operation using its stable identity. If payment succeeded but inventory ownership has been lost, attempt an explicitly allowed re-reservation or start a void/refund path; do not confirm unavailable inventory. Record compensation progress until it succeeds or enters manual repair, preserving the original outcome.

## Knowledge check

### 1. Does compensation restore every outside observer to the original state?

No. Effects such as notifications, fees, and observations may be irreversible.

### 2. Why persist the coordinator's state?

A restarted coordinator must resume or repair the workflow without forgetting completed steps or issuing contradictory actions.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Saga Orchestration Pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)

