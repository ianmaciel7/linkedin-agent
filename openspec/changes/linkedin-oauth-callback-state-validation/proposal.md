## Why

The local LinkedIn OAuth flow already generates a `state` value and receives it back on the callback, but it does not yet verify that the callback matches the request it initiated. That leaves the authentication foundation incomplete and weakens CSRF protection for the loopback browser flow called out in the roadmap.

## What Changes

- Add callback validation for the local loopback LinkedIn OAuth flow, including explicit handling for missing authorization codes, returned OAuth errors, missing `state`, and mismatched `state`.
- Define a consistent safe error contract for invalid callback payloads so the tool fails early without exchanging the authorization code.
- Add unit and integration coverage for successful callbacks and callback validation failures.
- Update roadmap and auth documentation to reflect that OAuth callback and state validation are part of the authentication foundation.

## Capabilities

### New Capabilities
- `linkedin-oauth-callback-validation`: validate loopback OAuth callback payloads before token exchange and reject unexpected or incomplete callback responses safely.

### Modified Capabilities

## Impact

- Affected code: `app/linkedin/oauth.py`, `app/tools/linkedin_oauth_service.py` if it needs to surface refined callback errors, and related unit/integration tests.
- Affected docs: `README.md` and any auth flow notes tied to the v0.1 roadmap.
- Security and privacy: improves OAuth CSRF protection for the local browser flow and must continue avoiding token, secret, and personal data exposure in logs or tool responses.
