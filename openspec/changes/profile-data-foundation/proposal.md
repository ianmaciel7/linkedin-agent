## Why

The agent can authenticate a user and confirm LinkedIn connectivity (v0.1.0), but it cannot yet identify who that user is beyond a raw OpenID Connect `userinfo` response. Without a stable member URN, user-supplied profile fields, and access to the authenticated member's posts, subsequent features—analytics, publishing, engagement—have no reliable identity anchor or content surface to work against.

## What Changes

- Add a new `member-urn` tool that resolves and stores the authenticated LinkedIn member's URN from the existing `/userinfo` response, making it reusable by all downstream tools without additional network calls.
- Add a `profile-data` tool that returns a structured summary of the authenticated member's publicly readable profile fields, blending OIDC-sourced data with user-supplied overrides for fields not available through the API.
- Add a `profile-data-store` service layer that persists the resolved member URN and user-supplied profile fields locally so they survive across sessions without re-prompting.
- Add a `post-reader` tool that retrieves the authenticated member's published posts from the LinkedIn Posts API (requires `r_member_social` scope, marked 🔒 in the roadmap) and normalises them into a stable metadata structure.
- Add a `post-metadata-store` service layer that persists retrieved post metadata and handles gracefully the case where posts are unavailable or the required API scope has not been granted.

## Capabilities

### New Capabilities

- `member-urn`: Resolve, store, and retrieve the authenticated LinkedIn member URN from the OIDC `sub` field; expose it through an ADK tool and a stable service API used by all other tools.
- `profile-data`: Assemble and return a structured member profile summary that merges OIDC-sourced fields with user-supplied overrides; persist the merged record locally across sessions.
- `post-reader`: Retrieve published posts for the authenticated member from the LinkedIn Posts API; normalize each post into a stable metadata model; handle permission-denied and empty-result cases safely.
- `post-metadata-store`: Persist, retrieve, and invalidate post metadata locally; handle unavailable posts and scope-gated access without crashing or leaking sensitive data.

### Modified Capabilities

- `linkedin-login-service`: Extend the OAuth result to include the resolved member URN when it is available, so callers receive identity context alongside the authentication confirmation.

## Impact

- **New ADK tools**: `resolve_member_urn`, `get_profile_data`, `read_member_posts` registered on `root_agent`.
- **New modules**: `app/linkedin/member.py` (URN resolution), `app/linkedin/profile.py` (profile assembly), `app/linkedin/posts.py` (Posts API client), `app/linkedin/profile_store.py` (local profile persistence), `app/linkedin/post_store.py` (local post-metadata persistence).
- **New models**: `MemberProfile`, `PostMetadata`, `PostMetadataStore` dataclasses in dedicated model modules under `app/linkedin/`.
- **Settings**: New optional environment variables `LINKEDIN_PROFILE_STORAGE_PATH` and `LINKEDIN_POST_STORAGE_PATH` for local persistence paths; no breaking changes to existing variables.
- **Scopes**: `r_member_social` required by `post-reader`; the tool MUST gracefully degrade when this scope is absent.
- **Dependencies**: No new runtime dependencies beyond `linkedin-api-client` already in the lockfile; `cryptography` already present for storage encryption.
- **Tests**: Unit tests for each new service and tool; integration tests with controlled fakes; at least one ADK eval case per user-visible flow.
- **Docs**: README roadmap items for v0.2.0 updated as each deliverable lands.
