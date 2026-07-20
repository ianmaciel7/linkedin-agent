## ADDED Requirements

### Requirement: Posts retrieved from LinkedIn Posts API
The system SHALL call the LinkedIn Posts API (`/rest/posts?author=<member_urn>&q=author`) using a valid access token and the `r_member_social` scope to retrieve the authenticated member's published posts.

#### Scenario: Posts retrieved successfully
- **WHEN** `read_member_posts` is called with a valid access token, a resolved member URN, and the `r_member_social` scope is granted
- **THEN** the system SHALL return a result with `ok: true` and a `posts` list containing normalised `PostMetadata` objects for each returned post

#### Scenario: No posts published
- **WHEN** the authenticated member has no published posts and the API returns an empty result set
- **THEN** the system SHALL return a result with `ok: true` and `posts: []` and an informational message noting that no posts were found

### Requirement: Post retrieval fails gracefully when scope is absent
The system SHALL return a structured `permission_denied` result when the `r_member_social` scope has not been granted for the current access token, and SHALL NOT raise an unhandled exception or return a misleading empty list.

#### Scenario: r_member_social scope not granted
- **WHEN** `read_member_posts` is called and LinkedIn returns HTTP 403 or a `PERMISSION_DENIED` service error code
- **THEN** the system SHALL return `ok: false`, `error_code: "permission_denied"`, and a `scope_required: "r_member_social"` field in the result

### Requirement: Post retrieval requires a resolved member URN
The system SHALL require a resolved member URN before calling the Posts API. If the URN is not available, the system SHALL return a structured error directing the caller to run `resolve_member_urn` first.

#### Scenario: Member URN not resolved
- **WHEN** `read_member_posts` is called and no member URN is available in the profile store or the current session
- **THEN** the system SHALL return `ok: false`, `error_code: "missing_configuration"`, and a message indicating that `resolve_member_urn` must be called first

### Requirement: Post metadata normalised before return
The system SHALL normalise each raw post from the LinkedIn API response into a `PostMetadata` object containing only: `post_urn`, `permalink`, `created_at`, `text_excerpt` (first 300 characters), `visibility`, `like_count`, and `comment_count`. Raw API payloads SHALL NOT be returned to the tool caller.

#### Scenario: Post normalisation strips excess fields
- **WHEN** the LinkedIn Posts API returns a post with reshared content, media attachments, or fields beyond the normalised set
- **THEN** the system SHALL include only the fields in the `PostMetadata` model and discard the rest

### Requirement: First-page-only retrieval in v0.2.0
The system SHALL retrieve only the first page of posts (up to 20 posts) from the LinkedIn Posts API in v0.2.0. The result SHALL include a `pagination_note` field indicating that pagination is not yet supported.

#### Scenario: API returns more than 20 posts
- **WHEN** the member has more than 20 posts and the API response includes a pagination cursor
- **THEN** the system SHALL return only the first 20 normalised posts and SHALL include `pagination_note: "First page only; pagination not yet supported"` in the result

### Requirement: Post retrieval rate limiting and timeout handled
The system SHALL normalise HTTP 429 rate-limit responses and request timeout errors into structured error results rather than raising unhandled exceptions.

#### Scenario: Rate limit hit during post retrieval
- **WHEN** LinkedIn returns HTTP 429 during the posts API call
- **THEN** the system SHALL return `ok: false`, `error_code: "rate_limited"`, and a retry-later message

#### Scenario: Timeout during post retrieval
- **WHEN** the posts API call exceeds the configured timeout
- **THEN** the system SHALL return `ok: false`, `error_code: "timeout"`, and a retry-later message
