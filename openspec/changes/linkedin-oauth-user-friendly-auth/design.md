## Context

The ADK client owns the built-in credential request UI after `request_credential(...)` is called. In the current LinkedIn login flow that means the end user may only see a generic prompt with little context about what to click next. We want to preserve the ADK-managed OAuth flow while also returning enough safe metadata for the agent to explain the next step in plain language.

## Goals / Non-Goals

**Goals:**
- Preserve ADK-managed credential requests for the actual OAuth flow.
- Return a safe authorization URL and concise next-step guidance when auth is pending.
- Keep the guidance readable enough for the agent to present as a clickable Markdown link.

**Non-Goals:**
- Replacing ADK credential handling with a custom token flow.
- Exposing OAuth state, tokens, secrets, or callback payloads beyond what is already embedded in the authorization URL.
- Adding any LinkedIn mutation capability.

## Decisions

Return safe pending-auth guidance from the tool in addition to calling `request_credential(...)`.
Rationale: this keeps the runtime-compatible ADK auth behavior while giving the agent structured data it can convert into a friendlier reply. The alternative of skipping `request_credential(...)` would weaken the intended ADK auth integration.

Generate the authorization URL from the existing OAuth helper.
Rationale: the repository already knows how to build the LinkedIn authorization request safely. Reusing that helper avoids duplicate URL-building logic and keeps the output aligned with the configured auth settings.

Teach the agent instruction to surface the URL as a clickable link.
Rationale: the tool can return metadata, but the agent still needs a clear instruction to transform that into end-user language. The alternative of relying on raw tool output would remain too UI-dependent.

## Risks / Trade-offs

[Some ADK clients may still prioritize their own credential UI] -> Mitigation: keep the built-in flow and add guidance rather than trying to replace it.

[Returning an authorization URL could be mistaken for a custom OAuth flow] -> Mitigation: document that the URL is guidance for the same ADK-managed consent step, not a replacement for credential handling.
