---
name: linkedin-api-python-client
description: >
  Use this skill when working with the official LinkedIn Python client library
  (`linkedin-api-client`) in this repository: adding or reviewing LinkedIn API
  calls, mapping LinkedIn REST docs to `RestliClient` methods, wiring OAuth
  flows with `AuthClient`, or choosing scopes and request shapes for
  `/userinfo`, `/me`, `/posts`, ad accounts, and other LinkedIn APIs. Prefer it
  whenever a task mentions Rest.li, versioned LinkedIn APIs, 2-legged or
  3-legged OAuth, field projections, query tunneling, or the upstream
  `linkedin-developers/linkedin-api-python-client` examples.
metadata:
  author: OpenAI Codex
  license: Apache-2.0
  version: 0.1.0
---

# LinkedIn API Python Client Reference

Use this skill to keep LinkedIn integration work aligned with the official
client library and this repository's safety rules.

## Start here

1. Read `references/official-client.md` for the upstream client behavior,
   available methods, auth flows, and example patterns.
2. For repo-local usage, inspect `app/linkedin/client.py` and
   `app/settings.py` before changing LinkedIn wiring.
3. Keep read-only validation separate from mutating operations.
4. Require explicit user confirmation immediately before any externally visible
   LinkedIn action such as creating a post, sending a message, or modifying a
   profile.

## Repo guidance

- Prefer small typed adapters around `RestliClient` instead of scattering raw
  library calls across ADK wiring.
- Read configuration through the validated settings layer rather than directly
  from environment variables in business logic.
- Prefer `/userinfo` or another read-only endpoint for connectivity checks.
- Preserve timeout handling and normalized error mapping when extending the
  existing adapter.
- Treat tokens, member profile data, and drafts as sensitive.

## References

| Reference | When to read |
| --- | --- |
| `references/official-client.md` | Default reference for the package, auth flows, Rest.li method mapping, common endpoints, and repo-specific usage notes. |
| `app/linkedin/client.py` | Current read-only adapter around `RestliClient`, including timeout injection and status-code normalization. |
| `app/settings.py` | Environment variables and validation rules used by the current LinkedIn API test path. |

