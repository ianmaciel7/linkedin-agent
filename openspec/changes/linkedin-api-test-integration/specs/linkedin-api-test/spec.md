## ADDED Requirements

### Requirement: Read-only LinkedIn API test helper
The system SHALL provide a read-only LinkedIn API test helper that uses `linkedin-api-client` to verify the configured access token can reach a configurable LinkedIn test endpoint without creating, updating, or deleting LinkedIn data.

#### Scenario: Successful connectivity test
- **WHEN** the helper is called with a valid access token and reachable endpoint
- **THEN** it SHALL return a structured success result indicating the request completed successfully

#### Scenario: Read-only behavior
- **WHEN** the helper executes the connectivity test
- **THEN** it SHALL not publish posts, send messages, send invitations, or modify profile data

### Requirement: Validated LinkedIn API settings
The system SHALL validate LinkedIn API test configuration from environment variables before performing the request.

#### Scenario: Missing access token
- **WHEN** the access token setting is missing or empty
- **THEN** the system SHALL fail early with a clear validation error that identifies the missing setting

#### Scenario: Invalid timeout value
- **WHEN** the timeout setting is missing, non-numeric, or not positive
- **THEN** the system SHALL fail early with a clear validation error that identifies the invalid setting

### Requirement: Structured test result
The system SHALL return a structured result for the LinkedIn API test that distinguishes success from failure and preserves safe debugging detail without exposing secrets.

#### Scenario: Success result
- **WHEN** the test request succeeds
- **THEN** the returned result SHALL include a success flag and safe response metadata suitable for tests and future callers

#### Scenario: Failure result
- **WHEN** the test request fails
- **THEN** the returned result SHALL include a normalized error code and a safe message that does not reveal secrets

### Requirement: ADK tool exposure
The system SHALL expose the read-only LinkedIn API test helper through the ADK root agent so a caller can trigger the connectivity check without adding mutating LinkedIn capabilities.

#### Scenario: Root agent registers the helper
- **WHEN** the ADK app is imported
- **THEN** the root agent SHALL include the LinkedIn API test helper in its registered tools

#### Scenario: Tool remains read-only
- **WHEN** the root agent invokes the LinkedIn API test helper
- **THEN** it SHALL only perform the existing read-only connectivity check and SHALL not publish posts, send messages, send invitations, or modify profile data

### Requirement: Normalize upstream failures
The system SHALL normalize upstream HTTP failures into stable error categories for timeout, permission denial, rate limiting, non-2xx responses, and generic upstream failure.

#### Scenario: Permission denied
- **WHEN** LinkedIn responds with an authentication or authorization failure
- **THEN** the system SHALL classify the result as permission denied

#### Scenario: Rate limited
- **WHEN** LinkedIn responds with a rate limiting failure
- **THEN** the system SHALL classify the result as rate limited

#### Scenario: Non-2xx response
- **WHEN** LinkedIn responds with a non-2xx status that is not otherwise classified
- **THEN** the system SHALL classify the result as an upstream failure and preserve the status code
