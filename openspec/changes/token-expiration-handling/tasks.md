## 1. Token lifecycle support

- [x] 1.1 Extend the LinkedIn OAuth and token-store domain layer so callers can distinguish expired-but-refreshable credentials from invalid records.
- [x] 1.2 Implement a LinkedIn refresh-token exchange helper that uses the official token endpoint and normalizes terminal versus transient refresh failures.
- [x] 1.3 Update the secure token storage flow to persist refreshed credentials safely and clear stored records only for unrecoverable expiration or rejected refresh tokens.

## 2. Tool flow integration

- [x] 2.1 Update `app/tools/linkedin_login_service.py` to attempt refresh for eligible expired stored credentials before falling back to browser reauthorization.
- [x] 2.2 Update `app/tools/linkedin_api_check.py` to reuse the same refresh lifecycle handling and return stable safe error categories for non-refreshable or transient refresh failures.
- [x] 2.3 Keep logs and tool responses sanitized across refresh attempt, success, rejection, unavailable-refresh, and upstream-failure paths.

## 3. Verification and documentation

- [x] 3.1 Add or update unit tests for refresh success, missing refresh token, invalid-grant rejection, and transient refresh failure handling.
- [x] 3.2 Add or update integration tests and ADK eval coverage for login-service and API-test behavior when a stored credential expires.
- [x] 3.3 Update `README.md`, `.env.example`, and any relevant auth-flow documentation to explain token expiration, refresh expectations, and reauthorization fallback.
- [x] 3.4 Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `openspec validate --all`.
