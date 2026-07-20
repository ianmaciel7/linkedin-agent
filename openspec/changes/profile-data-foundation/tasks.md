## 1. Models and Shared Types

- [x] 1.1 Create `app/linkedin/models.py` with `MemberProfile`, `PostMetadata`, and `PostStoreRecord` dataclasses; add type annotations and docstrings
- [x] 1.2 Verify `app/linkedin/models.py` imports cleanly with `uv run python -c "from app.linkedin.models import MemberProfile, PostMetadata"`

## 2. Member URN Resolution

- [x] 2.1 Create `app/linkedin/member.py` with `resolve_member_urn(userinfo: dict) -> str` that derives `urn:li:member:<sub>` from the OIDC `sub` claim
- [x] 2.2 Add unit tests in `tests/unit/test_member.py` covering: successful derivation, missing `sub` field, empty `sub` value
- [x] 2.3 Create `app/tools/resolve_member_urn.py` as the ADK tool entry point; inject settings and credential resolution; return a structured dict result
- [x] 2.4 Register `resolve_member_urn` on `root_agent` in `app/agent.py`
- [x] 2.5 Add an integration test in `tests/integration/test_resolve_member_urn.py` with a fake credential and fake token store
- [x] 2.6 Add at least one ADK eval case in `tests/eval/datasets/basic-dataset.json` for the `resolve_member_urn` happy path

## 3. Profile Data Assembly and Storage

- [x] 3.1 Create `app/linkedin/profile_store.py` with `LinkedInProfileStore` interface and `LocalEncryptedProfileStore` implementation using Fernet encryption; mirror the shape of `token_store.py`
- [x] 3.2 Add `LINKEDIN_PROFILE_STORAGE_PATH` and `LINKEDIN_TOKEN_ENCRYPTION_KEY` reuse to `app/settings.py`; update `.env.example` and `README.md` configuration table
- [x] 3.3 Create `app/linkedin/profile.py` with `assemble_profile(userinfo: dict, user_supplied: dict | None, stored: MemberProfile | None) -> MemberProfile` that merges OIDC and user-supplied fields
- [x] 3.4 Add unit tests in `tests/unit/test_profile.py` covering: full OIDC merge, partial OIDC merge, user-supplied override, empty inputs
- [x] 3.5 Add unit tests in `tests/unit/test_profile_store.py` covering: save, load, missing-file default, decryption failure
- [x] 3.6 Create `app/tools/get_profile_data.py` as the ADK tool entry point; return structured result with `member_urn`, OIDC fields, `user_supplied`, and `stored` flag
- [x] 3.7 Register `get_profile_data` on `root_agent` in `app/agent.py`
- [x] 3.8 Add an integration test in `tests/integration/test_get_profile_data.py` with a fake store and fake userinfo response
- [x] 3.9 Add at least one ADK eval case for `get_profile_data` covering the full OIDC profile happy path

## 4. LinkedIn Login Service — Member URN Extension

- [x] 4.1 Modify `app/linkedin/login_service.py` to call `resolve_member_urn` and append `member_urn` to the login result when a stored URN is available; leave the result unchanged when no URN is present
- [x] 4.2 Update unit tests in `tests/unit/test_login_service.py` to cover: login with stored URN present, login without stored URN
- [x] 4.3 Update the `linkedin-login-service` canonical spec at `openspec/specs/linkedin-login-service/spec.md` to include the new `member_urn` field requirement (sync step; do not archive the change yet)

## 5. Posts API Client

- [x] 5.1 Create `app/linkedin/posts.py` with `LinkedInPostsClient` that wraps `RestliClient` to call `/rest/posts?author=<member_urn>&q=author` with `count=20`; normalise each raw post into `PostMetadata`
- [x] 5.2 Add `LINKEDIN_API_VERSION` header (`202412`) to the Posts API call per `linkedin-api-client` versioned API patterns
- [x] 5.3 Add unit tests in `tests/unit/test_posts.py` covering: successful retrieval, empty list, permission denied (403), rate limited (429), timeout, missing member URN
- [x] 5.4 Add `r_member_social` to `.env.example` as a commented scope note

## 6. Post Metadata Store

- [x] 6.1 Create `app/linkedin/post_store.py` with `LinkedInPostStore` interface and `LocalEncryptedPostStore` implementation using Fernet encryption; atomic write pattern (write to temp, rename)
- [x] 6.2 Add `LINKEDIN_POST_STORAGE_PATH` to `app/settings.py`; update `.env.example` and `README.md`
- [x] 6.3 Add unit tests in `tests/unit/test_post_store.py` covering: save list, load list, clear, unavailable-post marking, missing-file default, decryption failure
- [x] 6.4 Create `app/tools/read_member_posts.py` as the ADK tool entry point; resolve member URN, call `LinkedInPostsClient`, persist to store, return structured result with `posts`, `stored`, and `pagination_note`
- [x] 6.5 Register `read_member_posts` on `root_agent` in `app/agent.py`
- [x] 6.6 Add an integration test in `tests/integration/test_read_member_posts.py` with a fake transport, fake URN store, and fake post store
- [x] 6.7 Add ADK eval cases for `read_member_posts` covering: scope-granted happy path, permission-denied graceful result, missing URN error

## 7. Documentation and README

- [x] 7.1 Mark `[ ] Build and store the authenticated member URN` complete in `README.md` v0.2.0 section once tasks 2.1–2.6 pass
- [x] 7.2 Mark `[ ] Import user-supplied profile information` complete in `README.md` once tasks 3.1–3.9 pass
- [x] 7.3 Mark `[ ] Read the authenticated member's posts 🔒` complete in `README.md` once tasks 5.1–5.4 and 6.1–6.7 pass
- [x] 7.4 Mark `[ ] Store post metadata and handle unavailable posts` complete in `README.md` once task 6.3 passes
- [x] 7.5 Update `README.md` configuration table with `LINKEDIN_PROFILE_STORAGE_PATH` and `LINKEDIN_POST_STORAGE_PATH`

## 8. Validation

- [ ] 8.1 `uv run pytest tests/unit/` — all unit tests pass
- [x] 8.2 `uv run pytest tests/integration/` — all integration tests pass
- [x] 8.3 `uv run ruff check .` — no lint errors
- [x] 8.4 `uv run ruff format --check .` — no formatting issues
- [x] 8.5 `openspec validate --all` — no spec validation errors
