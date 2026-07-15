## Why

The repository can already persist encrypted LinkedIn OAuth credentials, but an expired stored access token currently leads straight to credential clearing and reauthorization. That leaves the v0.1 authentication foundation incomplete because token expiration is expected in normal OAuth use, and local users should not be forced through a fresh browser sign-in when a safe refresh path is available.

## What Changes

- Add explicit token expiration handling for stored LinkedIn OAuth credentials, including refresh-capable recovery before falling back to reauthorization.
- Define how the login service and LinkedIn API check classify expired, refreshed, refresh-failed, and non-refreshable credentials.
- Persist refreshed credentials back into secure local storage without exposing raw tokens in logs or tool responses.
- Add configuration, test, and evaluation coverage for successful refresh, refresh rejection, missing refresh tokens, and safe fallback behavior.
- Keep the scope read-only and local-first; this change does not add LinkedIn write actions, background refresh jobs, or hosted credential storage.

## Capabilities

### New Capabilities
- `linkedin-token-expiration`: handle stored LinkedIn OAuth credential expiration, refresh eligible credentials safely, and require reauthorization only when refresh cannot succeed.

### Modified Capabilities
- None.

## Impact

- Affected code: `app/linkedin/`, `app/tools/`, `app/settings.py`, and the auth-related unit, integration, and eval test suites.
- Affected external behavior: LinkedIn OAuth token lifecycle handling during local browser login and ADK-backed connectivity checks.
- Configuration and dependencies: may require validated refresh-token-related settings already available through current OAuth settings, but should avoid introducing new external services or unsafe storage paths.
- Safety and privacy: touches sensitive credential lifecycle logic and must continue to keep tokens, refresh tokens, secrets, and unnecessary account data out of logs, docs, and tool responses.
