# Tasks: LinkedIn API Test Integration

1. Add a small LinkedIn API test helper/service that performs a read-only request with typed inputs and outputs.
2. Decide whether the helper uses LinkedIn's official Python client or a minimal HTTP fallback, and keep the choice narrow to the test path.
3. Add a settings layer or extend the existing one so the access token, endpoint URL, and timeout are validated from environment variables.
4. Add unit tests for configuration validation and request/result handling.
5. Add an integration test that exercises the helper with a fake client or stubbed transport.
6. Update `README.md` and `.env.example` to document the test flow and required variables if the implementation introduces or changes any settings.
7. If the official client is introduced, add and lock the dependency in `pyproject.toml` and regenerate `uv.lock`.
8. Run the relevant verification commands: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `openspec validate --all`.
