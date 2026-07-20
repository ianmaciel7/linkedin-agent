## Why

The current LinkedIn OAuth flow relies on ADK credential callbacks when no cached credential is available. In the local playground this has proven fragile: the runtime may inject a different redirect URI than the repository configuration, and stale auth callback IDs can produce runtime errors before the OAuth flow completes.

## What Changes

- Prefer a repo-controlled local browser OAuth flow when `LINKEDIN_REDIRECT_URI` points to `localhost` or `127.0.0.1`.
- Keep the ADK credential flow as a fallback for non-local redirect URIs.
- Return the same safe read-only OAuth result after the local browser flow completes.

## Capabilities

### Modified Capabilities
- `linkedin-login-service`: reliable local OAuth sign-in without depending on ADK playground credential callback IDs.

## Impact

- Affected code: `app/tools/linkedin_oauth_service.py`, `app/linkedin/oauth.py`, related tests, and `README.md`.
- Security and privacy: the local flow must still avoid exposing tokens or extra profile data in tool responses.
