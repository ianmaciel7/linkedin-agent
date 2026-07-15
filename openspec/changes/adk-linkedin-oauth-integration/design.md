## Context

The current repository can call LinkedIn only when a user manually provides `LINKEDIN_ACCESS_TOKEN` through environment configuration. That works for direct testing, but it is not the intended ADK pattern for authenticated external tools and it places token acquisition outside the agent experience. The new design needs to preserve the existing read-only connectivity boundary while shifting credential acquisition, caching, and reuse into an ADK-managed OAuth flow.

This change affects multiple modules: ADK tool registration in `app/agent.py`, tool orchestration in `app/tools/`, LinkedIn client behavior in `app/linkedin/`, and validated configuration in `app/settings.py`. It also introduces security-sensitive handling for LinkedIn client credentials, access tokens, refresh tokens, and consent boundaries.

## Goals / Non-Goals

**Goals:**
- Let the ADK tool request LinkedIn authorization when no valid credential is present.
- Store and reuse LinkedIn credentials through ADK credential APIs instead of requiring a pasted `LINKEDIN_ACCESS_TOKEN`.
- Keep the first authenticated flow strictly read-only and limited to connectivity verification.
- Preserve the existing small-adapter structure so LinkedIn HTTP logic remains testable without full ADK execution.
- Document the required LinkedIn app configuration and runtime secrets clearly.

**Non-Goals:**
- Posting to LinkedIn, sending messages or invitations, or editing profiles.
- Building a broad LinkedIn SDK wrapper beyond what the read-only connectivity path needs.
- Adding scraping, browser automation, or policy-sensitive workarounds.
- Committing secrets, persisting raw tokens in logs, or storing unnecessary profile data.

## Decisions

Use ADK authenticated-tool flow instead of manual token environment variables.
Rationale: ADK’s documented authentication pattern is the correct integration point for third-party OAuth. It allows the tool to request credentials when needed with `request_credential(...)`, inspect the returned auth material with `get_auth_response(...)`, and persist or reload credential state with `save_credential(...)` and `load_credential(...)`. The main alternative was continuing to accept `LINKEDIN_ACCESS_TOKEN` as the primary runtime contract, but that keeps the most fragile and user-hostile part of the integration outside ADK.

Keep LinkedIn API calls behind a narrow typed adapter.
Rationale: The existing `linkedin-api-client` transport boundary is already a good seam for tests and error normalization. The OAuth work should supply access credentials to that adapter rather than pushing raw LinkedIn request logic into ADK callbacks or agent instructions. The alternative was moving all request logic into one authenticated tool function, but that would make testing and future expansion harder.

Use LinkedIn’s official OAuth flow and read-only scopes only.
Rationale: The repository should rely on LinkedIn’s supported OAuth authorization code flow and the minimum scopes needed for `/userinfo` or equivalent read-only identity checks. The alternative of using unofficial flows or broader scopes would increase risk without helping the current use case.

Prefer `ToolContext` credential methods, with session scope as the initial storage policy.
Rationale: ADK exposes auth-specific credential APIs rather than requiring raw token handling in generic state. The implementation should prefer `load_credential(...)` and `save_credential(...)` for persisted auth material, while still allowing normal session state for lightweight control flags. Session scope remains the safest starting policy because it avoids creating long-lived token stores before the project actually needs cross-session reuse. The alternative of writing tokens to local files or custom databases would add security and migration complexity too early.

Use a tool-function-driven auth flow as the default implementation pattern.
Rationale: The simplest documented ADK path is for the LinkedIn connectivity tool to accept `tool_context`, check for existing credentials via ADK auth APIs, and call `request_credential(...)` when authorization is needed. A `before_tool_callback` remains a valid secondary option if the project later wants centralized auth orchestration across multiple tools, but it adds another moving part that the first version does not need.

Keep a clearly documented boundary between credential acquisition and external action.
Rationale: Successful authentication must not be interpreted as permission to perform mutating LinkedIn actions. The tool contract and agent instruction should explicitly frame the OAuth path as enabling only the read-only connectivity check. The alternative of bundling future write actions into the same auth proposal would blur safety boundaries.

## Risks / Trade-offs

[LinkedIn OAuth setup can be slow or confusing] -> Mitigation: document the exact LinkedIn app settings, redirect URI expectations, and scope requirements in README and `.env.example`.

[ADK auth integration may introduce tool-callback complexity] -> Mitigation: keep the first version limited to one read-only tool, prefer the direct `tool_context` auth path, and add callbacks only if centralization becomes necessary.

[Session-scoped credentials may require re-authentication more often than users want] -> Mitigation: accept that trade-off initially and defer persistent token storage until a later, explicit design change.

[Permission mismatches between LinkedIn products/scopes and requested endpoints can cause 401/403 failures] -> Mitigation: preserve normalized error mapping and document the required LinkedIn products and scopes as part of the setup flow.

[Refresh-token support may depend on LinkedIn app capabilities] -> Mitigation: design the tool to work with re-authorization if refresh is unavailable, and treat refresh handling as best-effort rather than a prerequisite.
