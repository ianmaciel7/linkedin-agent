## Why

The repository can authenticate a user and verify read-only LinkedIn access, but it still relies on short-lived session reuse or manually provided environment tokens. That leaves the authentication foundation incomplete for local development and future runtime services, because tokens are not persisted in a controlled, revocable, and auditable way.

## What Changes

- Add a secure local token storage layer for LinkedIn OAuth credentials so successful sign-in can be reused without exposing raw tokens in source control, logs, or tool responses.
- Encrypt persisted credential material at rest and scope stored records to the current LinkedIn application and authenticated account metadata needed for safe reuse.
- Define safe behavior for missing storage configuration, unreadable stored credentials, expired tokens, and revoked tokens.
- Keep token persistence strictly read-only in effect: storing credentials improves authenticated access continuity but does not grant permission for any LinkedIn mutation capability.
- Add documentation and verification coverage for configuration, storage lifecycle, corruption handling, and secret-safe logging.

## Capabilities

### New Capabilities
- `linkedin-token-storage`: securely persist, load, refresh, and clear LinkedIn OAuth credentials needed for continued authorized read-only access.

### Modified Capabilities
- None.

## Impact

- Affected code: `app/linkedin/`, `app/settings.py`, `app/tools/`, and related unit/integration tests.
- Affected docs: `README.md` and `.env.example` for storage configuration, secret handling, and local setup expectations.
- Dependencies: may require a vetted encryption or keyring dependency if the repository cannot satisfy at-rest protection with the current stack.
- Systems and operations: introduces local credential persistence, secret derivation or storage configuration, and credential lifecycle handling for logout, expiry, and invalidation paths.
