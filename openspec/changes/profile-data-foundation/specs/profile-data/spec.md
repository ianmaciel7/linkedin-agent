## ADDED Requirements

### Requirement: Profile data assembled from OIDC fields
The system SHALL return a structured `MemberProfile` that includes at minimum the `sub`, `name`, `given_name`, `family_name`, and `email` fields sourced from the LinkedIn OIDC `/userinfo` response when those fields are present.

#### Scenario: Full OIDC profile returned
- **WHEN** `get_profile_data` is called with a valid access token and the OIDC response contains all standard fields
- **THEN** the system SHALL return a result with `ok: true` and a `profile` object containing `member_urn`, `name`, `given_name`, `family_name`, and `email`

#### Scenario: Partial OIDC profile returned
- **WHEN** the OIDC `/userinfo` response omits optional fields such as `email`
- **THEN** the system SHALL return a result with `ok: true` and a `profile` object that includes only the fields that are present, without placeholders or nulls for absent optional fields

### Requirement: User-supplied profile fields accepted and merged
The system SHALL accept user-supplied profile fields (such as `headline`, `industry`, `location`) as optional tool input and SHALL merge them into the stored `MemberProfile`, preferring user-supplied values over OIDC-sourced defaults when both are present.

#### Scenario: User supplies headline and location
- **WHEN** `get_profile_data` is called with `user_supplied: {headline: "...", location: "..."}` and a valid access token
- **THEN** the system SHALL store those values in the profile record and return them in the result under a `user_supplied` key distinct from the OIDC-sourced fields

#### Scenario: User-supplied fields survive session restart
- **WHEN** user-supplied profile fields have been persisted in a previous session and `get_profile_data` is called in a new session without providing them again
- **THEN** the system SHALL return the previously stored user-supplied fields alongside the freshly resolved OIDC fields

### Requirement: Profile stored encrypted at rest
The system SHALL persist the assembled `MemberProfile` to an encrypted file at the path configured by `LINKEDIN_PROFILE_STORAGE_PATH` using the same Fernet encryption scheme as the token store.

#### Scenario: Profile persisted after assembly
- **WHEN** `get_profile_data` succeeds and `LINKEDIN_PROFILE_STORAGE_PATH` is configured
- **THEN** the system SHALL write the encrypted profile to the configured path and include `stored: true` in the result

#### Scenario: Profile retrieval when storage is not configured
- **WHEN** `LINKEDIN_PROFILE_STORAGE_PATH` is not set
- **THEN** the system SHALL still return the assembled profile for the current session without error, but SHALL omit `stored: true` from the result

### Requirement: Profile not returned without valid authentication
The system SHALL return a structured `permission_denied` or `missing_configuration` error when `get_profile_data` is called without a valid access token or stored credential, and SHALL NOT return cached profile data belonging to a previously authenticated member.

#### Scenario: Unauthenticated call
- **WHEN** `get_profile_data` is called without a valid access token and without a stored credential
- **THEN** the system SHALL return `ok: false` with `error_code: "missing_configuration"` and no profile data

### Requirement: Sensitive profile fields excluded from logs
The system SHALL NOT log `email`, raw OIDC tokens, or full profile payloads. Operational logs MAY record the `member_urn` and `credential_source` only.

#### Scenario: Profile assembly error
- **WHEN** an error occurs during profile assembly or storage
- **THEN** the system SHALL log a safe diagnostic message without including `email`, raw token content, or full profile JSON
