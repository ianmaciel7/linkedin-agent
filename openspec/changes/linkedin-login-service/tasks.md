## 1. Service boundary

- [x] 1.1 Define the LinkedIn login service contract, including structured inputs, safe outputs, and tool docstrings.
- [x] 1.2 Wire the login service into the ADK app without expanding the scope beyond sign-in and read-only verification.
- [x] 1.3 Update runtime settings and documentation references for the LinkedIn OAuth configuration used by the login flow.

## 2. OAuth flow and safety

- [x] 2.1 Implement ADK-managed credential request, reuse, and persistence for the LinkedIn login flow.
- [x] 2.2 Reuse the existing LinkedIn client adapter to confirm authenticated access and normalize upstream failures.
- [x] 2.3 Keep credential material and private identity data out of logs and user-facing tool responses.

## 3. Tests and verification

- [x] 3.1 Add unit tests for OAuth configuration validation, credential handling, and safe result shaping.
- [x] 3.2 Add integration tests for authorization-required, authorization-reused, permission-denied, and upstream-failure scenarios.
- [x] 3.3 Add or update an ADK evaluation case so the agent routes login requests to the LinkedIn login service and not to unrelated tools.

## 4. Documentation and validation

- [x] 4.1 Update `README.md` and `.env.example` with the LinkedIn login setup, required environment variables, and secret-handling notes.
- [x] 4.2 Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `openspec validate --all`.
