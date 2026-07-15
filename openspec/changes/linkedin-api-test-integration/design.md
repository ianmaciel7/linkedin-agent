# Design: LinkedIn API Test Integration

## Overview
Add a minimal LinkedIn API test helper that can be exercised in tests without mutating LinkedIn data, then expose that same helper through the ADK root agent.

The design should keep the LinkedIn-facing logic in a small, typed helper module so it can be unit-tested and stubbed cleanly, while keeping agent wiring thin and declarative.

Use `linkedin-api-client` behind a narrow adapter for the read-only test path so request construction stays centralized and the helper remains easy to stub.

## Proposed structure

- `app/agent.py`
  - Register the read-only LinkedIn API test helper as an ADK tool on `root_agent`.
  - Keep the agent instruction explicit that the tool is for credential and endpoint verification only.
- `app/linkedin/`
  - Own the LinkedIn-specific HTTP/client logic.
  - Expose a small function or client method for the read-only test request.
  - Wrap `linkedin-api-client` behind a narrow injectable adapter for the read-only test request.
- `tests/integration/`
  - Validate the helper behavior using a fake HTTP client or local test double.

## Behavior
The test flow should:

1. Read a LinkedIn access token from configuration.
2. Call a configurable read-only LinkedIn endpoint.
3. Return a structured result indicating success or failure.
4. Preserve enough error detail for debugging without exposing secrets.
5. Be callable through the ADK root agent without enabling any mutating LinkedIn action.

## Configuration
The implementation should use validated settings for:

- LinkedIn access token
- Test endpoint URL
- Request timeout
- Optional client-specific settings required by `linkedin-api-client`, if any.

If required configuration is missing, the tool should fail early with a clear error that identifies the missing setting.

## Helper contract
The helper should clearly document:

- When callers should use it.
- What inputs it accepts.
- What result it returns.

The result should be structured, not just free-form text, so tests and future callers can rely on it.

## Testing approach

- Unit test the deterministic request-building and validation logic.
- Integration test the helper with a fake client so no live LinkedIn request is needed.
- Keep `linkedin-api-client` behind an injectable adapter so tests can stub it without network calls.
- Add a unit-level regression test that confirms the ADK root agent registers the tool.
- Cover:
  - Success
  - Missing configuration
  - Upstream HTTP failure
  - Non-2xx response handling

## Risks and mitigations

- Risk: leaking tokens or response content in logs.
  - Mitigation: sanitize errors and avoid logging secrets or full payloads.
- Risk: coupling agent wiring to HTTP logic.
  - Mitigation: keep the HTTP client behind a small service boundary and make `app/agent.py` only register the exported tool.
- Risk: accidental expansion into mutating workflows.
  - Mitigation: keep the first version strictly read-only.
