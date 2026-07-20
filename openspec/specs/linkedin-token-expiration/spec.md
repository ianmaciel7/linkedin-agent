## Purpose

Define accepted behavior for expired LinkedIn credential refresh and reauthorization decisions.

## Requirements

### Requirement: Refresh eligible expired LinkedIn credentials
The system SHALL attempt an official LinkedIn OAuth token refresh before reauthorization when a stored credential is expired and includes the refresh material required for recovery.

#### Scenario: Expired stored credential is refreshed successfully
- **WHEN** the OAuth service or LinkedIn API check loads an expired stored credential that includes a usable refresh token
- **THEN** the system SHALL exchange that refresh token through the configured LinkedIn token endpoint, persist the refreshed credential in secure storage, and continue the read-only connectivity flow without requiring a new user authorization step

### Requirement: Reauthorize only when refresh cannot restore access
The system SHALL require a fresh LinkedIn authorization flow only when the stored credential is non-refreshable or the provider rejects refresh as no longer valid.

#### Scenario: Expired credential has no refresh token
- **WHEN** the system detects that a stored LinkedIn credential is expired and no usable refresh token is available
- **THEN** the system SHALL clear the expired stored credential and SHALL return a safe result that requires the user to authorize LinkedIn again

#### Scenario: Refresh token is rejected
- **WHEN** the LinkedIn token endpoint rejects a stored refresh token as invalid, revoked, or otherwise not recoverable
- **THEN** the system SHALL clear the stored credential, SHALL not retry the rejected refresh token indefinitely, and SHALL require a fresh authorization flow before continuing

### Requirement: Stable handling for transient refresh failures
The system SHALL distinguish transient refresh transport or upstream failures from terminal credential invalidation.

#### Scenario: Refresh request hits a transient upstream failure
- **WHEN** the system attempts to refresh an expired stored credential and the LinkedIn token endpoint times out, rate limits, or returns another transient upstream failure
- **THEN** the system SHALL return a normalized safe failure result, SHALL not expose raw token endpoint payloads or secret values, and SHALL preserve or replace stored state in a way that allows a later retry without forcing immediate reauthorization

### Requirement: Secret-safe refresh observability
The system SHALL keep refresh lifecycle logging and tool responses free of access tokens, refresh tokens, authorization codes, client secrets, and unnecessary private account data.

#### Scenario: Refresh lifecycle event is recorded
- **WHEN** the system records that refresh was attempted, succeeded, was unavailable, was rejected, or failed transiently
- **THEN** the recorded metadata and any returned user-facing result SHALL contain only sanitized lifecycle details and SHALL exclude raw credential material
