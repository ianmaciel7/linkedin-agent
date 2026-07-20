## MODIFIED Requirements

### Requirement: ADK-managed LinkedIn OAuth
The system SHALL acquire LinkedIn authorization for the OAuth service through ADK-managed OAuth rather than requiring a manually pasted access token for normal operation.

#### Scenario: Authorization required
- **WHEN** the OAuth service runs without a valid cached credential
- **THEN** the system SHALL request LinkedIn authorization through the ADK execution context
- **AND** it SHALL return safe guidance the agent can use to show the user a direct authorization link and clear next steps
