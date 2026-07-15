## 1. Callback Validation

- [x] 1.1 Add loopback callback validation that requires a non-empty expected `state` before opening the local OAuth trust boundary.
- [x] 1.2 Reject callback payloads with missing `state`, mismatched `state`, missing authorization codes, or provider-returned OAuth errors before token exchange.
- [x] 1.3 Preserve safe, user-readable error messages without logging tokens, secrets, or unnecessary callback data.

## 2. Verification Coverage

- [x] 2.1 Add unit tests for successful loopback callbacks, missing `state`, mismatched `state`, missing authorization code, and OAuth error callbacks.
- [x] 2.2 Add or update integration coverage to verify the login service surfaces callback validation failures cleanly and does not continue into token exchange.

## 3. Documentation And Validation

- [x] 3.1 Update `README.md` to reflect OAuth callback and state validation in the v0.1 authentication foundation and any relevant auth-flow notes.
- [x] 3.2 Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `openspec validate --all`.
