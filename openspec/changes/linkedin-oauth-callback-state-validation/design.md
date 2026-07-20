## Context

The repository already supports a loopback browser OAuth flow for LinkedIn by generating an authorization URL, opening the browser, waiting for the callback, exchanging the authorization code, and then calling `/userinfo`. That flow currently captures the callback `state` but does not validate it against the generated request before proceeding to token exchange. Because this is part of the authentication foundation and touches sensitive credential handling, the change benefits from an explicit design before implementation.

## Goals / Non-Goals

**Goals:**
- Enforce callback payload validation before exchanging a LinkedIn authorization code.
- Reject missing or mismatched `state` values with safe, user-readable errors.
- Keep the validation logic close to the existing OAuth helper so the browser flow remains a single, testable path.
- Expand tests and docs to cover the validated callback behavior.

**Non-Goals:**
- Adding persistent token storage.
- Changing the non-loopback ADK-managed OAuth flow.
- Expanding the repository into mutating LinkedIn actions or broader session management.

## Decisions

Validate callback payloads inside the loopback OAuth helper before token exchange.
Rationale: `wait_for_oauth_callback(...)` already owns callback parsing and returns the browser-flow result consumed by the rest of the login path. Enforcing validation there keeps the trust boundary narrow and avoids duplicated checks in callers.
Alternative considered: validate later in `run_linkedin_oauth_browser_smoke_test(...)`. Rejected because the invalid callback would already have crossed the helper boundary and future callers could forget to enforce the same rule.

Require an expected `state` for loopback flows and compare it to the callback `state`.
Rationale: the local flow already generates a request-specific `state`, so the safest path is to fail closed if the request lacks an expected `state` or the callback omits or changes it.
Alternative considered: tolerate a missing callback `state` when a code is present. Rejected because it weakens CSRF protection and leaves room for ambiguous callback handling.

Return safe validation errors and stop before code exchange.
Rationale: callback validation failures should be deterministic local errors, not downstream token-exchange errors. Failing early produces clearer behavior and avoids unnecessary network calls or secret handling.
Alternative considered: continue into token exchange and let LinkedIn reject bad requests. Rejected because it obscures the root cause and expands the surface area of an invalid callback.

Cover success and failure modes with focused unit tests plus tool-level integration checks.
Rationale: most behavior is deterministic and belongs in unit tests around the OAuth helper, while integration tests should verify that the OAuth tool surfaces the refined failure path correctly.

## Risks / Trade-offs

[Strict validation may reject callbacks from older or partially misconfigured local setups] -> Mitigation: use explicit error messages that call out missing or mismatched `state` so the failure is diagnosable.

[Validation logic in the callback helper increases coupling to the generated authorization request] -> Mitigation: pass the expected `state` from the generated request through an explicit parameter or validated result shape rather than relying on implicit global state.

[Documentation can drift from the implemented login behavior] -> Mitigation: update the README roadmap item and auth flow notes in the same change as the code and tests.

## Migration Plan

No data migration is required. Rollout is code-only: ship the validation changes, update tests, and document the stricter loopback callback contract. If the change causes unexpected local issues, rollback is limited to reverting the helper and tests.

## Open Questions

No open questions at proposal time.
