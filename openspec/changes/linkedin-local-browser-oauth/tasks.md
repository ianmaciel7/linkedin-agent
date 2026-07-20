## 1. Local OAuth flow

- [x] 1.1 Detect loopback redirect URIs and run the local browser OAuth flow directly from the LinkedIn OAuth service.
- [x] 1.2 Keep ADK credential requests as the fallback for non-local redirect URIs.

## 2. Verification

- [x] 2.1 Add tests for local browser preference and ADK fallback behavior.
- [x] 2.2 Run relevant tests, lint, and `openspec validate --all`.
