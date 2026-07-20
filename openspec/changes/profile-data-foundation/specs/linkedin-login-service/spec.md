## MODIFIED Requirements

### Requirement: Login result includes member URN when available
The system SHALL include a `member_urn` field in the login service success result when the URN has already been resolved and stored, so that callers receive identity context alongside the authentication confirmation without a separate tool call.

#### Scenario: Login succeeds with stored URN
- **WHEN** the login service completes successfully and a resolved member URN is present in the profile store
- **THEN** the system SHALL include `member_urn` in the result alongside `ok: true` and the existing `account_summary`

#### Scenario: Login succeeds without stored URN
- **WHEN** the login service completes successfully and no member URN has been resolved yet
- **THEN** the system SHALL return a result with `ok: true` and SHALL omit `member_urn` from the result without error

#### Scenario: Read-only boundary preserved
- **WHEN** the login service completes successfully with or without a member URN
- **THEN** the system SHALL not publish posts, send messages, send invitations, or modify profile data
