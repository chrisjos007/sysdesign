# Authentication, authorization, and tenant isolation

ID: sd-23 | Level: Advanced | Stage 4: Operate reliably | Suggested study: 40 minutes

Prerequisites: sd-02, sd-08, sd-09

[Curriculum map](../curriculum-map.md) · [Catalogue](../catalogue.json)

## Learning objectives

- Separate identity verification from permission decisions.
- Carry trusted tenant scope through every data path.
- Test object-level authorization and isolation under pooling.

## Intuition

Authentication answers who is making a request. Authorization answers whether that identity may perform this action on this resource now. In a multi-tenant service, a valid login is only the beginning: one customer's data must not leak into another customer's responses.

## How it works

Use a trusted identity/session mechanism with appropriate lifecycle controls, then evaluate permissions server-side for the requested object and action. OWASP's object-level authorization guidance emphasizes checking access whenever client-supplied identifiers select records. Random IDs do not replace that check. PostgreSQL row-level security can enforce row policies, but superusers, BYPASSRLS roles, and normally table owners bypass them. Connection pooling also means tenant-specific session state must not leak between borrowers.

Technical references: [Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html); [API1:2023 Broken Object Level Authorization](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/); [Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html).

## Worked example

Tenant A and tenant B each have report number 17. A cache key report:17 is ambiguous even if the SQL query correctly filters by tenant. Use a key scoped to the authorized tenant and relevant representation, and recheck any required permissions. A queued export must carry a trusted tenant identity and the appropriate authorization policy; blindly copying tenant_id from a request body lets a caller choose another tenant's data.

## Trade-offs and failure modes

Per-tenant databases provide stronger resource and operational separation at higher management cost. Shared tables simplify operation but demand disciplined predicates, constraints, roles, and tests. A global administrator needs explicit, audited scope rather than accidental bypass. Public error messages should not reveal whether another tenant's private object exists. Revoking membership also requires decisions about sessions, cached authorization, queued tasks, and already-issued download capabilities.

## Practice

List tests for an API that reads, updates, deletes, and exports tenant documents. Include a valid user changing an object ID, a pooled connection previously used by another tenant, and a cache hit created under a different role.

### Answer guidance

For every action, assert that the server derives tenant membership from trusted identity and enforces object/action scope. Test cross-tenant IDs, stale role changes, cache scope, background jobs, and connection reuse. Use application database roles representative of production; tests run only as an owner/superuser can conceal row-policy mistakes.

## Knowledge check

### 1. Does an unguessable UUID authorize access?

No. It reduces guessing but is not a permission check.

### 2. Is enabling row-level security enough when the application connects as a superuser?

No. Superusers bypass row security; the role and policy configuration are part of the guarantee.

## Mastery checkpoint

Explain the worked example without notes, complete the practice task, and justify both knowledge-check answers. Revisit any prerequisite needed to explain your reasoning.

## Sources and scope

Sources reviewed 2026-09-27. The examples, workloads, exercises, and proposed choices are original teaching scenarios, not production measurements. Product-specific behavior belongs to the linked version or documentation checked on that date.

- [Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [API1:2023 Broken Object Level Authorization](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/)
- [Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)

