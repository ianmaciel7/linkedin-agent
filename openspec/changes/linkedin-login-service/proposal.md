## Why

The repository already has LinkedIn connectivity helpers, but the login and authorization path is still spread across environment setup and reusable utilities. A small, explicit OAuth service will make the authentication boundary clearer for the agent while keeping the scope limited to sign-in and read-only verification.

## What Changes

- Add a lightweight LinkedIn OAuth service that requests authorization through ADK, reuses a cached credential when available, and returns a structured sign-in result.
- Validate the LinkedIn OAuth configuration before starting authorization so missing or malformed settings fail fast.
- Keep LinkedIn credentials, tokens, and private member data out of logs and tool responses.
- Preserve a strict read-only boundary for login and verification only; no posting, messaging, invitations, or profile edits are included.
- Add tests and documentation for the login flow, credential reuse, and safe failure handling.

## Capabilities

### New Capabilities
- `linkedin-login-service`: ADK-managed LinkedIn sign-in and read-only verification for a simple, reusable login flow.

### Modified Capabilities
- None.

## Impact

- Affected code: `app/linkedin/oauth.py`, `app/linkedin/client.py`, `app/tools/`, `app/settings.py`, `app/agent.py`, and related tests.
- Affected docs: `README.md` and `.env.example` for LinkedIn OAuth setup and secret handling.
- Dependencies: no new external dependency is expected for the first version.
- Security and privacy: LinkedIn tokens, client secrets, and private identity data must remain out of source control, logs, and user-facing responses.
