## Context

The current login and connectivity flows can reuse encrypted stored credentials, but the token store raises an expired-credential error before callers can inspect whether the stored record also contains a refresh token. As a result, both `app/tools/linkedin_oauth_service.py` and `app/tools/linkedin_api_check.py` clear the record and force reauthorization whenever `expires_at` is in the past, even though the OAuth credential may still be recoverable through the LinkedIn token endpoint.

This change is cross-cutting because expiration handling touches the token store contract, OAuth client behavior, login-tool orchestration, settings validation, documentation, and auth-related test coverage. It must preserve the existing read-only boundary, continue to use official OAuth flows, and keep credential lifecycle telemetry sanitized.

## Goals / Non-Goals

**Goals:**
- Allow the system to inspect expired stored credentials safely enough to determine whether refresh is possible.
- Refresh eligible stored LinkedIn OAuth credentials through the official token endpoint before requesting a fresh browser or ADK authorization flow.
- Classify refresh outcomes consistently across the local browser OAuth path and the ADK-backed API check path.
- Persist refreshed credentials back into encrypted local storage and keep raw credential material out of logs and tool responses.
- Add proportionate unit, integration, and eval coverage for refresh success, refresh rejection, non-refreshable expiration, and transient upstream failures.

**Non-Goals:**
- Adding any LinkedIn write capability, background scheduler, or autonomous token refresh daemon.
- Introducing hosted secret management, multi-user credential storage, or deployment-time migrations.
- Retrying refresh indefinitely or masking upstream outages behind silent reauthorization loops.
- Storing broader account profile payloads or other session state with the credential record.

## Decisions

Expose an expiration-aware credential read path instead of treating all expired records as immediately unusable.
Rationale: the current `load()` API throws before callers can inspect `refresh_token`, which prevents a safe recovery attempt. The likely implementation is either a new token-store method that returns the stored record plus expiration status or a token-store result type that distinguishes `valid`, `expired_refreshable`, and `invalid`. The alternative of encoding refresh logic inside the token store would blur the boundary between persistence and OAuth transport behavior.

Centralize LinkedIn token refresh logic in the OAuth/domain layer and reuse it from both tool entry points.
Rationale: refresh is an OAuth protocol concern and belongs beside the existing authorization-code exchange logic in `app/linkedin/oauth.py`. The alternative of duplicating refresh HTTP calls in both tools would create drift in error handling and secret-safe logging.

Refresh only when the stored credential has a non-empty refresh token and the failure mode is normal expiration.
Rationale: refresh should be a targeted recovery path, not a blanket retry strategy for every unsuccessful API response. The alternative of refreshing on permission errors or arbitrary upstream failures could hide real configuration problems and create confusing lifecycle behavior.

Treat refresh rejection caused by revoked or invalid grants as a terminal credential failure that clears the stored record and requires reauthorization, while preserving the record for transient refresh transport failures.
Rationale: invalid-grant style errors mean the credential can no longer be recovered and should not remain cached. Timeouts, temporary 5xx responses, and rate limits are different; keeping the record allows a later retry without forcing the user through another consent flow. The alternative of clearing on every refresh failure would overreact to transient outages.

Keep observability limited to safe lifecycle categories such as refresh attempted, refresh succeeded, refresh rejected, refresh unavailable, and refresh upstream failure.
Rationale: token expiration handling needs debuggable state transitions without logging access tokens, refresh tokens, authorization codes, or full token endpoint payloads. The alternative of verbose OAuth logging would increase secret exposure risk.

## Risks / Trade-offs

[LinkedIn may not issue refresh tokens for all app products or scopes] -> Mitigation: specify a clean non-refreshable path that falls back to reauthorization without treating the absence of a refresh token as an unexpected error.

[Changing the token-store contract could ripple through multiple callers and tests] -> Mitigation: keep the interface narrow, update both tool entry points together, and add focused unit coverage around credential state transitions.

[Transient refresh failures may leave an expired credential cached and cause repeated failed attempts] -> Mitigation: return a stable, user-safe failure category and rely on explicit subsequent retries rather than unbounded automatic retry loops.

[Refresh behavior can be mistaken for expanded mutation capability] -> Mitigation: document clearly that refresh only maintains authenticated read-only access and does not change LinkedIn action permissions.

## Migration Plan

No data migration is required for existing encrypted token files if the stored credential schema remains compatible. Rollout is local-code only: update the token lifecycle logic, refresh documentation, and test coverage together, and allow users with already expired cached credentials to retry sign-in under the new flow.

## Open Questions

- Does the current LinkedIn OAuth product configuration reliably return refresh tokens for the supported read-only flow, or must the implementation primarily optimize for the no-refresh fallback path?
- Should transient refresh endpoint failures surface through an existing normalized error code or introduce a dedicated refresh-specific category for clearer eval coverage?
