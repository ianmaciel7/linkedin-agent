# Tasks: LinkedIn API Test Integration

1. Add a small LinkedIn API test helper/service that performs a read-only request with typed inputs and outputs.
2. Decide whether the helper uses LinkedIn's official Python client or a minimal HTTP fallback, and keep the choice narrow to the test path.
3. Add a settings layer or extend the existing one so the access token, endpoint URL, and timeout are validated from environment variables.
4. Register the read-only LinkedIn API test helper on the ADK root agent without enabling mutating LinkedIn behavior.
5. Add unit tests for configuration validation, request/result handling, and ADK tool registration.
6. Add an integration test that exercises the helper with a fake client or stubbed transport.
7. Update `README.md` and `.env.example` to document the test flow and required variables if the implementation introduces or changes any settings.
8. If the official client is introduced, add and lock the dependency in `pyproject.toml` and regenerate `uv.lock`.
9. Run the relevant verification commands: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `openspec validate --all`.
## 1. Planning artifacts

- [x] 1.1 Add a delta spec for the LinkedIn API test helper with read-only, validation, and error-handling requirements.
- [x] 1.2 Keep the task breakdown aligned with the spec and design before implementation begins.

## 2. LinkedIn API test helper

- [x] 2.1 Implement a small typed LinkedIn API test service/helper outside ADK wiring.
- [x] 2.2 Add a narrow `linkedin-api-client` adapter so the helper can be exercised with a fake client.
- [x] 2.3 Add structured success and failure result types with safe error normalization.

## 3. Settings and documentation

- [x] 3.1 Add or extend validated settings for the access token, endpoint URL, and timeout.
- [x] 3.2 Update `.env.example` and `README.md` to document the test flow and required variables.
- [x] 3.3 Keep secrets and private response data out of logs and error messages.

## 4. Tests and verification

- [x] 4.1 Add unit tests for settings validation and helper result mapping.
- [x] 4.2 Add an integration test that exercises the helper with a fake client or stubbed transport.
- [x] 4.3 Add and lock the `linkedin-api-client` dependency with `uv add linkedin-api-client` and regenerate `uv.lock`.
- [ ] 4.4 Register the read-only helper on the ADK root agent.
- [ ] 4.5 Add a regression test that confirms the ADK root agent exposes the helper.
- [ ] 4.6 Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `openspec validate --all`.
