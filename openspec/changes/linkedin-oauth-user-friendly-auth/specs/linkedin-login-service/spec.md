## MODIFIED Requirements

### Requirement: ADK-managed LinkedIn login
The system SHALL acquire LinkedIn authorization for the login service through ADK-managed OAuth rather than requiring a manually pasted access token for normal operation.

#### Scenario: Authorization required
- **WHEN** the login service runs without a valid cached credential
- **THEN** the system SHALL request LinkedIn authorization through the ADK execution context
- **AND** it SHALL return safe guidance the agent can use to show the user a direct authorization link and clear next steps
