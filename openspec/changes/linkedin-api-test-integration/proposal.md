# LinkedIn API Test Integration

## Problem
The agent needs a very small, safe way to verify that LinkedIn credentials and the configured API endpoint are working before we build broader LinkedIn workflows.

Right now, there is no documented, spec-backed plan for a read-only API test helper that lives outside ADK and can be exercised in tests.

## Intended outcome
Add a simple, non-mutating LinkedIn API test helper that:

- Confirms the configured access token can reach the LinkedIn test endpoint.
- Returns structured success or failure information.
- Is covered by automated tests so the integration remains stable.
- Uses LinkedIn's official Python API client where it simplifies request construction.

## Scope
This change will cover:

- A small LinkedIn API test service/helper outside the ADK layer.
- A controlled integration test that validates the helper behavior with a fake or stubbed HTTP client.
- Documentation updates for required environment variables and local verification steps.
- If the official client is used, a pinned dependency entry for it in `pyproject.toml`.

## Non-goals
This change will not:

- Publish posts, send messages, send invitations, or modify profile data.
- Add scraping, bulk outreach, evasion, or other policy-sensitive automation.
- Implement full OAuth flows, token refresh, or a broader LinkedIn client abstraction unless required for the test path.
- Wire the test into `root_agent` or add other ADK behavior.
- Introduce production deployment changes.
- Build a full-purpose LinkedIn SDK wrapper beyond what the test helper needs.

## User impact
The user will be able to run a simple LinkedIn API connectivity test to confirm configuration before attempting broader workflow automation.

## Safety and privacy
The test must remain read-only and must not store or log secrets, private response bodies, or personal data beyond what is necessary to report success or failure.

## Dependencies
- Existing ADK app wiring in `app/`.
- Existing environment variable configuration for LinkedIn access and endpoint settings.
- `pytest` for automated verification.
