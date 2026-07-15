## 1. OAuth configuration and tool contract

- [x] 1.1 Define and validate the LinkedIn OAuth configuration needed for ADK-managed authorization, including client ID, client secret, redirect URI, and any flow-specific settings.
- [x] 1.2 Update the LinkedIn connectivity tool contract so it accepts `ToolContext`-driven auth flow inputs and no longer depends on a manually supplied `LINKEDIN_ACCESS_TOKEN` for normal operation.

## 2. Authenticated LinkedIn tool implementation

- [x] 2.1 Implement the preferred `ToolContext`-driven ADK auth flow using `request_credential(...)` and `get_auth_response(...)` for the LinkedIn connectivity tool.
- [x] 2.2 Persist and reload LinkedIn auth material with ADK credential APIs such as `save_credential(...)` and `load_credential(...)`, using session scope as the initial policy.
- [x] 2.3 Adapt the LinkedIn client adapter to accept ADK-managed credentials while preserving read-only endpoint behavior and normalized error handling.
- [x] 2.4 Keep agent instructions and tool registration explicit that successful authentication does not permit posts, messages, invitations, or profile edits.
- [x] 2.5 Evaluate whether a `before_tool_callback` is still needed after the direct tool-context implementation, and only add it if it reduces duplication without weakening clarity.

## 3. Verification and safety coverage

- [x] 3.1 Add unit tests for OAuth configuration validation, ADK credential API usage, credential persistence behavior, and safe result shaping.
- [x] 3.2 Add integration tests for authorization-required, authorization-reused, permission-denied, and upstream-failure scenarios using fakes or controlled test doubles.
- [x] 3.3 Add or update ADK evaluation coverage for the read-only LinkedIn auth flow so the agent chooses the tool only for connectivity verification requests.

## 4. Documentation and validation

- [x] 4.1 Update `README.md`, `.env.example`, and any setup notes to document LinkedIn app configuration, ADK auth flow expectations, and secret-handling rules.
- [x] 4.2 Update dependency and runtime configuration documentation if ADK auth helpers or additional libraries are required, regenerating `uv.lock` when dependencies change.
- [x] 4.3 Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `openspec validate --all`.
