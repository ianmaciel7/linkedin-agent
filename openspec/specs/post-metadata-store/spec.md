## Purpose

Define accepted behavior for encrypted persistence and retrieval of normalized LinkedIn post metadata.

## Requirements

### Requirement: Post metadata stored to encrypted file
The system SHALL persist retrieved `PostMetadata` records as an encrypted JSON file at the path configured by `LINKEDIN_POST_STORAGE_PATH` using Fernet encryption. Each store operation SHALL replace the entire post index atomically.

#### Scenario: Post metadata persisted after retrieval
- **WHEN** `read_member_posts` succeeds and `LINKEDIN_POST_STORAGE_PATH` is configured
- **THEN** the system SHALL write the normalised `PostMetadata` list to the encrypted store and include `stored: true` in the result

#### Scenario: Storage not configured
- **WHEN** `LINKEDIN_POST_STORAGE_PATH` is not set
- **THEN** the system SHALL return post metadata in-memory for the current session only, without error, and SHALL omit `stored: true` from the result

### Requirement: Stored post metadata retrievable without re-fetching API
The system SHALL expose a retrieval path that reads the encrypted post store and returns the cached `PostMetadata` list without making an API call when fresh data is not explicitly requested.

#### Scenario: Cached posts returned from store
- **WHEN** post metadata has been previously persisted and `read_member_posts` is called with `use_cache: true`
- **THEN** the system SHALL return the cached `PostMetadata` list with `source: "post_store"` and SHALL NOT call the LinkedIn Posts API

### Requirement: Unavailable posts handled gracefully
The system SHALL handle the case where a stored post URN no longer resolves to a live post (e.g., the post was deleted by the member) by marking it as `unavailable: true` in the store rather than raising an error or removing the record silently.

#### Scenario: Previously stored post deleted
- **WHEN** a stored post URN is no longer returned by the Posts API on a subsequent retrieval
- **THEN** the system SHALL mark that record as `unavailable: true` in the store and retain it so that analytics features in v0.3.0 can account for deleted posts

### Requirement: Post store cleared on explicit request
The system SHALL allow the post metadata store to be cleared via an explicit `clear: true` parameter on the tool or via a dedicated service call, after which subsequent reads return an empty list until the API is called again.

#### Scenario: Post store cleared
- **WHEN** the post store clear operation is called
- **THEN** the system SHALL delete the encrypted post store file and return `ok: true` with a confirmation message

### Requirement: Post store does not expose raw post text in logs
The system SHALL NOT log post text excerpts, post URNs, or member URNs at INFO level or above. Debug-level logging of post counts and store file paths is permitted.

#### Scenario: Post store write error
- **WHEN** writing the encrypted post store fails due to a filesystem error
- **THEN** the system SHALL log a safe diagnostic message containing only the store path and error type, without including post text or member identity data
