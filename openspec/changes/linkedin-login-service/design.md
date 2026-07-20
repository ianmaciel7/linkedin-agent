## Context

This repository already contains LinkedIn OAuth helpers, a read-only API adapter, and a tool that can request authorization through ADK. The remaining gap is an explicit, simple OAuth service boundary that makes sign-in behavior obvious and reusable without expanding into broader LinkedIn automation.

The design must fit the existing ADK app structure, keep credentials and tokens private, and preserve the platform boundary that externally visible LinkedIn actions require explicit approval before execution. For this change, the scope stays limited to sign-in and read-only verification.

## Goals / Non-Goals

**Goals:**
- Provide a small LinkedIn OAuth service that can request authorization, reuse cached credentials, and confirm authenticated access.
- Keep OAuth configuration validation explicit and safe.
- Return structured results that are useful for the agent but do not leak secrets or unnecessary profile data.
- Reuse the existing LinkedIn client and OAuth helpers instead of duplicating network logic.
- Keep the read-only boundary clear so a successful login does not imply permission for mutating LinkedIn actions.

**Non-Goals:**
- Posting, messaging, invitations, profile edits, or any other outward-facing LinkedIn action.
- Building a general-purpose LinkedIn SDK wrapper.
- Introducing custom token storage outside the ADK credential flow.
- Adding scraping, browser automation, or policy-sensitive workarounds.

## Decisions

Use ADK-managed OAuth through the tool execution context instead of a manual token prompt.
Rationale: the agent should request authorization in a first-class way rather than asking the user to paste tokens. The main alternative was to keep a manual `LINKEDIN_ACCESS_TOKEN` path as the primary contract, but that would leave the most fragile part of authentication outside the ADK flow.

Keep the OAuth service thin and delegate LinkedIn HTTP work to the existing adapter.
Rationale: the repository already has a read-only LinkedIn client with normalized error handling. Reusing that adapter keeps the OAuth service focused on credential acquisition and safe result shaping. The alternative of embedding raw HTTP calls inside the tool would increase duplication and make testing harder.

Prefer session-scoped credential reuse through ADK credential APIs.
Rationale: session reuse is the simplest safe starting point and avoids introducing custom persistence before the project needs it. The alternative of writing tokens to files or a custom database would add security and migration complexity too early.

Return only structured success/failure metadata, not raw OAuth material.
Rationale: the agent needs to know whether login succeeded and, at most, a minimal identity summary. Exposing access tokens or refresh tokens would create avoidable privacy and security risk. The alternative of returning full credential objects would be unsafe and unnecessary.

Keep the agent instruction and tool contract explicitly read-only.
Rationale: authentication should never be interpreted as permission for mutations. The alternative of bundling future write actions into the same change would blur the safety boundary and make review harder.

## Risks / Trade-offs

[OAuth setup can be slow or confusing] -> Mitigation: document the required LinkedIn app settings, redirect URI, and scope expectations clearly in the repository docs.

[Session-scoped credential reuse may require reauthorization more often] -> Mitigation: accept that trade-off for v1 and defer longer-lived storage to a later change if needed.

[LinkedIn may reject requests because of scope or product mismatch] -> Mitigation: preserve normalized permission-denied errors and keep the OAuth result safe and actionable.

[The current implementation already contains nearby OAuth helpers, so overlap is possible] -> Mitigation: keep this change narrowly focused on the OAuth service boundary and avoid broad refactors.
