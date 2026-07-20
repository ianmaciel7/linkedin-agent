## Context

The agent has a working authentication foundation (v0.1.0): it can OAuth-authenticate a LinkedIn user, confirm connectivity via `/userinfo`, and store an encrypted credential locally. However, the system has no stable identity anchor beyond the raw OIDC response fields, no way to remember user-supplied profile enrichments across sessions, and no way to read or index the authenticated member's published posts.

v0.2.0 builds the identity and content layer that every subsequent feature depends on: analytics needs to measure against a known member URN; publishing needs to POST on behalf of an identified member; engagement needs to operate on posts whose metadata is already normalised and stored locally.

Current modules of note:
- `app/linkedin/client.py`: Read-only REST client backed by `linkedin-api-client`.
- `app/linkedin/oauth.py`: OAuth flow, token exchange, and OIDC integration.
- `app/linkedin/login_service.py`: Orchestrates the full login flow.
- `app/tools/linkedin_api_check.py`: ADK tool that confirms connectivity.
- `app/settings.py`: Pydantic-based settings layer reading from environment.

## Goals / Non-Goals

**Goals:**
- Resolve and persist the authenticated LinkedIn member URN derived from the OIDC `sub` claim.
- Assemble and return a structured member profile summary that merges OIDC-sourced fields with user-supplied overrides.
- Persist the merged profile record locally so it survives across sessions without re-prompting the user.
- Retrieve published posts for the authenticated member via the LinkedIn Posts API (`/rest/posts`) and normalise them into a stable metadata model.
- Persist retrieved post metadata locally; handle unavailable or scope-gated posts gracefully.
- Expose three new ADK tools: `resolve_member_urn`, `get_profile_data`, `read_member_posts`.
- Add a delta spec for the `linkedin-login-service` capability to include the member URN in login results.

**Non-Goals:**
- Editing or publishing posts (v0.4.0).
- Follower counts or post analytics (v0.3.0).
- Engagement actions such as reactions or replies (v0.5.0).
- Session or memory service configuration (v0.6.0).
- Any write path to LinkedIn profile fields.

## Decisions

### D1: Member URN derived from OIDC `sub`, not a separate API call

**Decision:** Derive the member URN by wrapping the `sub` claim from the `/userinfo` response as `urn:li:member:<sub>` rather than calling the `/v2/me` endpoint.

**Rationale:** The `sub` claim is already available in the authenticated session at zero additional network cost. The `/v2/me` endpoint requires the `r_liteprofile` scope which is not always granted. URN derivation from `sub` is documented LinkedIn practice and keeps the happy path scope-minimal.

**Alternative considered:** Call `/v2/me` for a richer identity payload. Rejected because it introduces a new required scope and a fragile second network call in the login critical path.

### D2: Profile data stored as an encrypted JSON file alongside the token store

**Decision:** Persist `MemberProfile` as an encrypted JSON file at a path configured via `LINKEDIN_PROFILE_STORAGE_PATH`, using the same `cryptography.fernet` pattern as the token store.

**Rationale:** Reusing the established encryption pattern avoids introducing a new dependency (e.g., SQLite) and keeps the storage model consistent. Profile data is PII and must be encrypted at rest.

**Alternative considered:** Plain JSON. Rejected because profile fields such as `email` and `name` are personal data that must be protected.

### D3: Post metadata stored as an encrypted JSON index, not raw API payloads

**Decision:** Store only normalised `PostMetadata` fields (URN, permalink, creation time, title/text excerpt, visibility, like count, comment count) rather than full API response blobs.

**Rationale:** Raw API payloads are large, version-coupled, and may carry sensitive reshared content. Storing only the normalised model reduces footprint, keeps the schema stable, and avoids persisting unnecessary personal data from reshared posts.

### D4: `r_member_social` scope gating is a graceful degradation, not a hard failure

**Decision:** The `read_member_posts` tool MUST return a clear, structured `permission_denied` result when the required scope is absent rather than raising an exception or returning an empty list silently.

**Rationale:** Most LinkedIn developer accounts do not have `r_member_social` approved by default. A graceful result with `error_code: "permission_denied"` and a descriptive message lets the agent inform the user and suggests next steps without crashing the session.

### D5: New modules follow the single-responsibility convention already in `app/linkedin/`

**Decision:** Add four sibling modules: `member.py` (URN resolution), `profile.py` (profile assembly), `posts.py` (Posts API client), and `profile_store.py` / `post_store.py` (persistence). Dataclass models live in a new `app/linkedin/models.py`.

**Rationale:** Existing modules each own one concern (client, oauth, token_store, login_service). Following that pattern keeps the file graph readable and avoids the "one file owns everything" anti-pattern called out in AGENTS.md.

### D6: Tools are thin entry points; business logic lives in service modules

**Decision:** Each new ADK tool function in `app/tools/` delegates immediately to a service in `app/linkedin/`. Tool files contain only type annotations, docstrings, settings/client instantiation, and result formatting.

**Rationale:** Consistent with `linkedin_api_check.py` → `client.py` pattern. Keeps tools testable by swapping service fakes without ADK context.

## Risks / Trade-offs

- **`r_member_social` scope availability** → Mitigation: D4 graceful degradation; the spec requires a clear `permission_denied` result with `scope_required` metadata.
- **URN format stability** → Mitigation: The `urn:li:member:<sub>` pattern is documented in LinkedIn's API docs and used by the existing `linkedin-api-client` examples; pin the format and add a unit test for the derivation.
- **Profile storage path collision with token store** → Mitigation: Use separate configurable paths; default filenames are `linkedin_profile.enc` and `linkedin_posts.enc` to avoid collision.
- **Post API pagination** → Mitigation: v0.2.0 reads only the first page (up to 20 posts) to keep the scope narrow; pagination is explicitly noted as a v0.3.0+ concern.
- **PII in post text excerpts** → Mitigation: Store only the first 300 characters of post text; never log full post bodies.

## Migration Plan

1. All changes are additive. No existing tools, settings keys, or stored file formats are changed.
2. New optional environment variables (`LINKEDIN_PROFILE_STORAGE_PATH`, `LINKEDIN_POST_STORAGE_PATH`) have safe defaults (no storage) when not set; the tools work without them, storing results only in memory for the session.
3. No `uv.lock` changes expected; all required libraries are already in the lockfile.
4. `uv sync` + `uv run pytest` must pass after each task before proceeding to the next.

## Open Questions

- Should `get_profile_data` attempt to call `/v2/me` for additional fields (headline, industry) when `r_liteprofile` is available, or limit itself to OIDC fields only in v0.2.0? **Tentative decision:** OIDC-only in v0.2.0; `/v2/me` enrichment is a v0.3.0 candidate.
- Should the `resolve_member_urn` result be automatically appended to the login service result, or returned only on explicit tool invocation? **Tentative decision:** Both — the login service appends it when the URN is already resolved; the standalone tool is the explicit path.
