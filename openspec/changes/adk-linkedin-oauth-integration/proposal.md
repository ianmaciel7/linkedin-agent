## Why

The current LinkedIn integration path depends on a manually supplied `LINKEDIN_ACCESS_TOKEN`, which is useful for connectivity testing but is not the recommended long-term ADK pattern for authenticated external tools. We need a spec-backed plan for an ADK-managed OAuth flow so the agent can request, cache, and reuse LinkedIn credentials safely without hardcoding or manually pasting tokens.

## What Changes

- Add an ADK-authenticated LinkedIn tool flow that requests LinkedIn member authorization when credentials are missing or expired.
- Replace the manual-token-first runtime path with an OAuth-managed credential path for the read-only LinkedIn connectivity check.
- Define how LinkedIn OAuth client settings, redirect handling, token caching, and read-only scope selection should work in this repository.
- Add tests and documentation for the authenticated tool flow, including safe handling of missing consent, expired credentials, and permission failures.

## Capabilities

### New Capabilities
- `linkedin-adk-oauth`: ADK-managed OAuth authentication for the read-only LinkedIn connectivity tool, including credential acquisition, caching, refresh behavior, and safe invocation boundaries.

### Modified Capabilities
<!-- None. This change introduces a new capability and does not modify any accepted canonical spec yet. -->

## Impact

- Affected code: [`app/agent.py`](/home/ianma/workspace/linkedin-agent/app/agent.py), [`app/tools/linkedin_api_check.py`](/home/ianma/workspace/linkedin-agent/app/tools/linkedin_api_check.py), [`app/linkedin/client.py`](/home/ianma/workspace/linkedin-agent/app/linkedin/client.py), [`app/settings.py`](/home/ianma/workspace/linkedin-agent/app/settings.py), and related tests.
- Affected systems: LinkedIn OAuth application configuration and ADK tool authentication flow.
- Sensitive data: LinkedIn client secret, access tokens, refresh tokens, and member profile claims must remain out of source control and logs.
- Dependencies and configuration: may require ADK auth helper usage and additional LinkedIn OAuth configuration such as client ID, client secret, and redirect URI.
- Deployment/runtime impact: local and deployed environments will need the OAuth client configuration even when tokens are no longer supplied manually.
