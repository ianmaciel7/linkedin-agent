## Context

The current LinkedIn authentication foundation can complete OAuth and verify read-only access, but it does not yet provide a durable storage boundary for OAuth credentials. Existing changes intentionally stopped at session-scoped reuse to avoid premature persistence, and the roadmap now calls out secure token storage as the next missing piece in the v0.1 authentication foundation.

This change crosses multiple modules because credential persistence affects settings, OAuth helpers, the login tool boundary, tests, and repository documentation. The design must preserve the current read-only safety posture, keep secrets out of logs and user-facing responses, and avoid introducing storage behavior that is hard to revoke or migrate later.

## Goals / Non-Goals

**Goals:**
- Persist LinkedIn OAuth credential material locally in a way that protects tokens at rest.
- Keep storage access behind a small domain boundary so ADK wiring and LinkedIn HTTP logic remain separate.
- Support safe reuse, refresh, invalidation, and explicit clearing of stored credentials.
- Fail safely when storage is misconfigured, unreadable, corrupted, or contains credentials that no longer work.
- Document the required configuration and verification steps for developers using local environments.

**Non-Goals:**
- Shipping cloud-hosted secret management or multi-user tenancy in this change.
- Expanding scope into LinkedIn write actions, background scheduling, or workflow automation.
- Persisting unnecessary personal profile data alongside the credentials.
- Committing to a long-term runtime storage backend for future production deployments.

## Decisions

Introduce a dedicated token store interface in `app/linkedin/` and keep the login service dependent on that abstraction.
Rationale: a narrow storage contract keeps encryption, serialization, and file handling out of tool code and makes unit testing straightforward. The alternative of embedding persistence directly in the OAuth helper would blur responsibilities and make later backend changes harder.

Persist only the credential fields required for authorized reuse plus minimal lookup metadata.
Rationale: storing less reduces privacy and breach impact while still allowing the login flow to find and reuse the correct credential. The alternative of storing full `/userinfo` responses or broader session state would create avoidable sensitivity without helping the auth flow.

Use local encrypted-at-rest persistence configured through the validated settings layer.
Rationale: the repository already relies on environment-driven configuration, so storage location and encryption material should follow the same pattern. The alternative of plaintext local files is unacceptable, while introducing a cloud KMS or database now would add deployment complexity before the project needs it.

Treat unreadable, expired, revoked, or decryption-failed credentials as recoverable login-state failures and fall back to reauthorization after clearing the invalid record.
Rationale: stale credentials are expected in OAuth systems and should not require manual file surgery in normal cases. The alternative of repeatedly retrying broken credentials would create confusing failure loops.

Keep observability limited to safe lifecycle metadata such as store hit/miss, refresh attempt, invalidation path, and sanitized error categories.
Rationale: the team needs enough signal to debug auth behavior without ever logging tokens, secrets, raw callback payloads, or private account data. The alternative of verbose auth logging would materially increase secret exposure risk.

## Risks / Trade-offs

[A new encryption dependency may complicate local setup and packaging] -> Mitigation: prefer a well-supported library, keep the dependency surface narrow, and document setup clearly in `.env.example` and `README.md`.

[Local encrypted storage still depends on the safety of the developer machine and secret configuration] -> Mitigation: require explicit configuration, store only minimal credential material, and provide a clear path to clear stored credentials.

[Credential corruption or incompatible serialization could lock users into repeated reauth loops] -> Mitigation: version the stored record format and treat decode/decrypt failures as invalidation events with stable user-facing errors.

[This design is intentionally local-first and may not match a future hosted runtime backend] -> Mitigation: isolate storage behind an interface so a later runtime service can replace the implementation without rewriting the tool contract.
