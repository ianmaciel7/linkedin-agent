# Design: LinkedIn API Test Integration

## Overview
Add a minimal LinkedIn API test helper that lives outside ADK and can be exercised in tests without mutating LinkedIn data.

The design should keep the LinkedIn-facing logic in a small, typed helper module so it can be unit-tested and stubbed cleanly, without adding agent wiring.

Where the LinkedIn Python client library reduces request-construction complexity, use LinkedIn's official client instead of hand-rolling protocol details.

## Proposed structure

- `app/agent.py`
- `app/linkedin/`
  - Own the LinkedIn-specific HTTP/client logic.
  - Expose a small function or client method for the read-only test request.
  - Use the official LinkedIn Python client when practical, or a narrow HTTP fallback if the client does not cover the needed endpoint.
- `tests/integration/`
  - Validate the helper behavior using a fake HTTP client or local test double.

## Behavior
The test flow should:

1. Read a LinkedIn access token from configuration.
2. Call a configurable read-only LinkedIn endpoint.
3. Return a structured result indicating success or failure.
4. Preserve enough error detail for debugging without exposing secrets.

## Configuration
The implementation should use validated settings for:

- LinkedIn access token
- Test endpoint URL
- Request timeout
- Optional client-specific settings required by the official LinkedIn library, if any.

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
- If the official client is introduced, keep it behind an injectable adapter so tests can stub it without network calls.
- Cover:
  - Success
  - Missing configuration
  - Upstream HTTP failure
  - Non-2xx response handling

## Risks and mitigations

- Risk: leaking tokens or response content in logs.
  - Mitigation: sanitize errors and avoid logging secrets or full payloads.
- Risk: coupling agent wiring to HTTP logic.
  - Mitigation: keep the HTTP client behind a small service boundary and avoid ADK coupling.
- Risk: accidental expansion into mutating workflows.
  - Mitigation: keep the first version strictly read-only.
