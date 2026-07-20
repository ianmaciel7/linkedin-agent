## Context

The repository already contains a working local browser OAuth smoke flow that opens the LinkedIn consent page, listens on a local callback URI, exchanges the authorization code, and calls `/userinfo`. The ADK OAuth tool currently does not use that path for normal local sign-in; instead it calls `request_credential(...)` and depends on the playground runtime to finish the auth exchange. In practice that runtime can override the redirect target or lose the callback function ID, producing user-facing failures unrelated to LinkedIn credentials.

## Goals / Non-Goals

**Goals:**
- Make local OAuth sign-in deterministic when the configured redirect URI is local.
- Preserve the existing safe result shape and read-only boundary.
- Keep ADK-managed auth available for non-local redirect scenarios.

**Non-Goals:**
- Adding token persistence outside the current session.
- Expanding into mutating LinkedIn actions.
- Removing the existing manual auth-code helper functions.

## Decisions

Prefer the local browser flow for loopback redirect URIs.
Rationale: if the redirect target is a loopback address, the repository already has everything needed to own the entire OAuth round-trip. That avoids client-specific callback IDs and redirect rewriting.

Keep ADK credential requests for non-loopback redirect URIs.
Rationale: hosted or non-local environments may still need the runtime-managed auth flow, so the change should be selective rather than global.

Use the existing browser smoke helper instead of reimplementing the OAuth exchange.
Rationale: this keeps the OAuth logic in one place and reuses tested code paths for opening the browser, waiting for the callback, exchanging the code, and fetching `/userinfo`.

## Risks / Trade-offs

[Opening a browser from the tool may be surprising in some contexts] -> Mitigation: restrict it to explicit login requests with loopback redirect URIs and document the behavior.

[A local callback server can still fail if the port is unavailable] -> Mitigation: surface the existing safe OAuth error messages to the user.
