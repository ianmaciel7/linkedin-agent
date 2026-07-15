## Why

The LinkedIn login flow currently relies on the default ADK credential prompt when authorization is needed. That works technically, but it is not obvious to end users what they should click or whether there is a direct authorization link they can open.

## What Changes

- Return safe, user-friendly authorization guidance when the LinkedIn login tool is waiting for OAuth consent.
- Include a direct LinkedIn authorization URL in the pending-auth result so the agent can surface a clickable link.
- Update agent instructions, tests, and docs so the conversational response explains the next step clearly without exposing secrets.

## Capabilities

### Modified Capabilities
- `linkedin-login-service`: clearer pending-auth responses with safe authorization guidance for users.

## Impact

- Affected code: `app/agent.py`, `app/linkedin/oauth.py`, `app/tools/linkedin_api_check.py`, and related tests.
- Affected docs: `README.md`.
- Security and privacy: the returned guidance must not expose tokens, client secrets, or unnecessary identity data.
