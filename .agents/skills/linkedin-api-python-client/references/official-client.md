# Official LinkedIn API Python Client

Source repository: `https://github.com/linkedin-developers/linkedin-api-python-client`

## Overview

- Upstream package name: `linkedin-api-client`
- Upstream repository summary: official Python client library for LinkedIn APIs
- Upstream runtime requirement in the current `main` branch: Python 3.7+
- Primary dependency: `requests`
- Current upstream package status: beta; expect API and behavior changes

The library is a thin wrapper over LinkedIn's Rest.li APIs. Its main value is
correct request construction:

- adds the required Rest.li protocol behavior
- encodes complex query parameters and path keys
- supports versioned LinkedIn API requests
- automatically uses query tunneling when needed
- exposes OAuth helpers for member and application auth flows

## Main imports

```python
from linkedin_api.clients.restli.client import RestliClient
from linkedin_api.clients.auth.client import AuthClient
```

Use `RestliClient` for API calls and `AuthClient` for OAuth token flows.

## Read-only request pattern

For a simple member-info request, upstream documents a `GET /userinfo` flow:

```python
from linkedin_api.clients.restli.client import RestliClient

client = RestliClient()
response = client.get(
    resource_path="/userinfo",
    access_token=access_token,
)
profile = response.entity
```

This is the best fit for this repository's current connectivity check because it
is read-only and maps cleanly to the existing settings model.

## Auth flows

### 3-legged member auth

Use this when a user acts on their own LinkedIn account.

Core methods:

- `generate_member_auth_url(scopes, state=None)`
- `exchange_auth_code_for_access_token(code)`
- `exchange_refresh_token_for_access_token(refresh_token)`
- `introspect_access_token(access_token)`

Typical setup:

- `client_id`
- `client_secret`
- `redirect_url`
- approved LinkedIn product access
- correct scopes for the target endpoint

Upstream examples show member auth for `r_liteprofile` and then calling `/me`.

### 2-legged application auth

Use this only for APIs that support application access without a member context.

Core methods:

- `get_two_legged_access_token()`
- `introspect_access_token(access_token)`

Upstream notes that client-credentials auth is not enabled for most developer
apps by default, so do not assume it is available.

## RestliClient request shape

Every request starts with a `resource_path` and `access_token`. Optional
arguments are:

- `path_keys`: values for placeholders inside the path
- `query_params`: plain Python values; the client handles encoding
- `version_string`: LinkedIn version header value such as `202212` or
  `202212.01`

Important behaviors:

- `resource_path` is the path after the LinkedIn API base URL and should begin
  with `/`
- use placeholders like `/adAccounts/{id}` and pass the values in `path_keys`
- pass nested dicts and lists as normal Python values; the client encodes them
- versioned APIs require `version_string`
- calls are blocking

## Rest.li method map

Use the LinkedIn REST documentation first to decide which Rest.li method the
endpoint supports, then map it to the client method below.

Read operations:

- `get()`: fetch one entity
- `batch_get()`: fetch multiple entities by id
- `get_all()`: list a collection
- `finder()`: run a named finder
- `batch_finder()`: run a finder across multiple criteria sets

Write operations:

- `create()`
- `batch_create()`
- `update()`
- `batch_update()`
- `partial_update()`
- `batch_partial_update()`
- `delete()`
- `batch_delete()`
- `action()`

Guidance for this repo:

- default to read operations unless the user clearly asks for a mutating change
- stop for confirmation immediately before any `create`, `update`, `delete`, or
  `action` call that changes LinkedIn state

## High-value upstream examples

### `/userinfo`

- endpoint type: read-only
- typical use: connectivity checks, identity confirmation
- token/scopes: upstream README calls out `openid` and `profile` for the OpenID
  Connect flavor of Sign In with LinkedIn

### `/me`

- endpoint type: read-only
- typical use: fetch current member profile and derive the person URN
- field projections are supported through `query_params`

Example pattern:

```python
response = client.get(
    resource_path="/me",
    access_token=access_token,
    query_params={"fields": "id,firstName:(localized),lastName"},
)
```

### `/posts` and `/ugcPosts`

- endpoint type: mutating
- typical use: create feed posts
- extra caution: upstream example explicitly warns that this creates real,
  visible posts

In this repository, do not use these flows without explicit user confirmation at
execution time.

### Finder requests for ad accounts

Finder requests are the main example of why the client is helpful. Complex
objects inside `query_params` can be passed as normal dictionaries and the
client handles the Rest.li encoding.

Versioned example shape:

```python
response = client.finder(
    resource_path="/adAccounts",
    finder_name="search",
    query_params={"search": {...}},
    version_string="202212",
    access_token=access_token,
)
```

## Session customization

`RestliClient` exposes its underlying Requests session as `client.session`.
Useful patterns:

- add response hooks
- enforce `raise_for_status()`
- inject default timeout behavior at the adapter level

This repository currently wraps `session.send` to ensure a default timeout for
all library calls instead of relying on each caller to pass timeout arguments.

## Repo-specific mapping

Current local usage lives in [app/linkedin/client.py](/home/ianma/workspace/linkedin-agent/app/linkedin/client.py)
and [app/settings.py](/home/ianma/workspace/linkedin-agent/app/settings.py).

Important local behavior:

- `LinkedInApiSettings` reads:
  - `LINKEDIN_ACCESS_TOKEN`
  - `LINKEDIN_API_TEST_URL`
  - `LINKEDIN_API_TIMEOUT_SECONDS`
- default read-only test URL is `https://api.linkedin.com/v2/userinfo`
- `_resource_path_from_endpoint()` strips a `/v2` prefix before sending
  `resource_path` to `RestliClient`
- `RestliLinkedInTransport` injects a default timeout through the Requests
  session
- the adapter normalizes LinkedIn failures to:
  - `permission_denied` for `401` and `403`
  - `rate_limited` for `429`
  - `timeout` for `408` or transport timeout errors
  - `upstream_failure` otherwise

When extending the adapter, keep this normalization style unless there is a
spec-driven reason to change it, and update tests alongside the code.

## Suggested implementation approach in this repo

1. Start with a small typed adapter in `app/linkedin/`.
2. Keep token and endpoint configuration in the settings layer.
3. Normalize transport errors into repo-specific error codes before they reach
   ADK tools.
4. Unit-test response mapping without calling real LinkedIn services.
5. For mutating capabilities, split draft generation from execution and gate the
   execution step behind explicit confirmation.

## Upstream materials used

- Repository README: installation, overview, supported methods, and examples
- `examples/get_profile.py`: `/me` usage, field projections, and projection
  patterns
- `examples/create_posts.py`: `/me`, `/ugcPosts`, `/posts`, and mutation risk
- `examples/oauth_member_auth_redirect.py`: member auth redirect flow
- `examples/oauth_2legged.py`: client-credentials flow and token introspection
- Upstream `pyproject.toml`: package name, Python requirement, and dependency
  baseline
