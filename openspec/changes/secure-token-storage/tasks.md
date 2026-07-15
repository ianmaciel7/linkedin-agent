## 1. Storage foundation

- [ ] 1.1 Add validated settings for secure token storage location and encryption configuration.
- [ ] 1.2 Introduce a typed LinkedIn token store interface and local encrypted persistence implementation under `app/linkedin/`.
- [ ] 1.3 Version the stored credential record format and ensure only required credential fields plus minimal lookup metadata are serialized.

## 2. Auth flow integration

- [ ] 2.1 Update the LinkedIn login flow to load stored credentials before prompting for reauthorization.
- [ ] 2.2 Persist newly acquired credentials through the token store and invalidate stored records on expiry, revocation, corruption, or decryption failure.
- [ ] 2.3 Keep tool responses and logs limited to safe lifecycle metadata and stable failure categories.

## 3. Verification and docs

- [ ] 3.1 Add unit tests for token store serialization, encryption/decryption, invalidation, and corruption handling.
- [ ] 3.2 Add integration coverage for credential reuse, forced reauthorization, and storage-related auth failures.
- [ ] 3.3 Update `README.md` and `.env.example` with secure token storage setup, safety notes, and local verification steps.
- [ ] 3.4 Update dependencies and `uv.lock` if a new vetted encryption or keyring library is required.
- [ ] 3.5 Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `openspec validate --all`.
