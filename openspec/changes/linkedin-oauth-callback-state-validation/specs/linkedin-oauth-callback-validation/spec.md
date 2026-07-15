## ADDED Requirements

### Requirement: Loopback OAuth callback state validation
The system SHALL validate the callback payload for the repository-controlled loopback LinkedIn OAuth flow before exchanging an authorization code for an access token.

#### Scenario: Valid callback completes the browser flow
- **WHEN** the system generates a loopback LinkedIn authorization request with an expected `state`
- **AND** the callback returns a non-empty authorization code and the same `state`
- **THEN** the system SHALL treat the callback as valid
- **AND** it SHALL return the authorization code for the subsequent token exchange step

#### Scenario: Callback omits state
- **WHEN** the system generates a loopback LinkedIn authorization request with an expected `state`
- **AND** the callback returns an authorization code without a `state`
- **THEN** the system SHALL reject the callback before token exchange
- **AND** it SHALL return a safe validation error that explains the missing `state`

#### Scenario: Callback state does not match the request
- **WHEN** the system generates a loopback LinkedIn authorization request with an expected `state`
- **AND** the callback returns a different `state`
- **THEN** the system SHALL reject the callback before token exchange
- **AND** it SHALL return a safe validation error that explains the `state` mismatch

#### Scenario: OAuth provider returns an error callback
- **WHEN** the callback includes an OAuth `error`
- **THEN** the system SHALL stop the browser flow without attempting token exchange
- **AND** it SHALL surface a safe error that preserves the provider error code and optional description without exposing secrets

### Requirement: Fail-closed handling for incomplete loopback callback inputs
The system SHALL fail closed when the repository-controlled loopback OAuth flow cannot establish a trustworthy callback result.

#### Scenario: Authorization code is missing
- **WHEN** the callback reaches the configured loopback path without an OAuth `error`
- **AND** the callback does not include a non-empty authorization code
- **THEN** the system SHALL reject the callback
- **AND** it SHALL not call the LinkedIn token endpoint

#### Scenario: Expected state cannot be established
- **WHEN** the loopback OAuth flow cannot determine a non-empty expected `state` for the generated authorization request
- **THEN** the system SHALL fail the flow before waiting for the callback
- **AND** it SHALL return a safe local error instead of opening a callback trust boundary without state validation
