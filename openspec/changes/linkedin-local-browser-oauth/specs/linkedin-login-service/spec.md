## MODIFIED Requirements

### Requirement: ADK-managed LinkedIn login
The system SHALL acquire LinkedIn authorization for the login service through a safe OAuth flow rather than requiring a manually pasted access token for normal operation.

#### Scenario: Local authorization required
- **WHEN** the login service runs without a valid cached credential
- **AND** the configured LinkedIn redirect URI points to `localhost` or `127.0.0.1`
- **THEN** the system SHALL prefer the repository-controlled local browser OAuth round-trip

#### Scenario: Non-local authorization required
- **WHEN** the login service runs without a valid cached credential
- **AND** the configured LinkedIn redirect URI is not loopback-local
- **THEN** the system SHALL request LinkedIn authorization through the ADK execution context
