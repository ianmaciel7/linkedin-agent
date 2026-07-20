## ADDED Requirements

### Requirement: URN resolved from OIDC subject claim
The system SHALL derive the authenticated member URN by formatting the `sub` field from the LinkedIn OIDC `/userinfo` response as `urn:li:member:<sub>`.

#### Scenario: URN resolved successfully
- **WHEN** the authenticated OIDC session contains a non-empty `sub` claim
- **THEN** the system SHALL return a result with `ok: true` and a `member_urn` field set to `urn:li:member:<sub>`

#### Scenario: URN resolution attempted without authentication
- **WHEN** `resolve_member_urn` is called without a valid access token or stored credential
- **THEN** the system SHALL return a result with `ok: false` and `error_code: "missing_configuration"` describing that authentication is required

#### Scenario: OIDC response missing sub claim
- **WHEN** the OIDC `/userinfo` response is present but does not contain a `sub` field
- **THEN** the system SHALL return a result with `ok: false` and `error_code: "upstream_failure"` indicating the identity claim is absent

### Requirement: URN persisted for session reuse
The system SHALL store the resolved member URN locally when a `LINKEDIN_PROFILE_STORAGE_PATH` is configured so that subsequent tool calls within and across sessions can retrieve it without re-fetching `/userinfo`.

#### Scenario: URN stored after successful resolution
- **WHEN** the URN is resolved successfully and a profile storage path is configured
- **THEN** the system SHALL write the URN to the encrypted profile store and return `credential_source: "resolved"` in the result

#### Scenario: Stored URN reused on subsequent call
- **WHEN** `resolve_member_urn` is called and a valid URN is already present in the encrypted profile store
- **THEN** the system SHALL return that URN immediately with `credential_source: "profile_store"` without calling `/userinfo` again

### Requirement: URN not exposed in logs or raw responses
The system SHALL NOT write the member URN, OIDC `sub` value, or any other personal identifier to logs or error messages beyond the structured tool result.

#### Scenario: Error during URN derivation
- **WHEN** an error occurs during URN derivation or storage
- **THEN** the system SHALL return a safe error result without logging the OIDC `sub` value or raw token content
