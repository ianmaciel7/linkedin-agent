## Purpose

Define accepted behavior for ADK-managed LinkedIn authorization used by the read-only connectivity tool.

## Requirements

### Requirement: ADK-managed LinkedIn authorization
The system SHALL acquire LinkedIn credentials for the read-only connectivity tool through an ADK-managed OAuth flow instead of requiring a manually supplied `LINKEDIN_ACCESS_TOKEN` for normal operation.

#### Scenario: Authorization required
- **WHEN** the LinkedIn connectivity tool is invoked without a valid cached LinkedIn credential
- **THEN** the system SHALL initiate the ADK authentication flow needed to obtain LinkedIn authorization by requesting credentials through the tool execution context

#### Scenario: Authorization reused
- **WHEN** the LinkedIn connectivity tool is invoked with a valid cached LinkedIn credential for the session
- **THEN** the system SHALL reuse that credential without requiring the user to authorize again

### Requirement: ADK credential API usage
The system SHALL use ADK credential APIs as the primary mechanism for requesting, reading, and persisting LinkedIn auth material for the connectivity tool.

#### Scenario: Credential request
- **WHEN** the connectivity tool determines that authorization is required
- **THEN** it SHALL request credentials through ADK credential APIs instead of implementing a custom out-of-band token prompt

#### Scenario: Credential persistence
- **WHEN** the connectivity tool receives usable LinkedIn auth material from ADK
- **THEN** it SHALL persist and reload that material through ADK credential APIs instead of storing raw tokens only in generic session state

### Requirement: Read-only authenticated connectivity check
The system SHALL use the ADK-acquired LinkedIn credential only for the existing read-only connectivity check unless a future approved specification expands that scope.

#### Scenario: Successful authenticated connectivity test
- **WHEN** the user completes authorization and the configured read-only LinkedIn endpoint is reachable
- **THEN** the system SHALL return a structured success result for the connectivity check

#### Scenario: Read-only boundary preserved
- **WHEN** the connectivity tool runs after successful authorization
- **THEN** the system SHALL not publish posts, send messages, send invitations, or modify profile data

### Requirement: Validated OAuth configuration
The system SHALL validate the LinkedIn OAuth client configuration required for the ADK-managed authorization flow before attempting to start authorization.

#### Scenario: Missing OAuth client setting
- **WHEN** a required LinkedIn OAuth setting such as client ID, client secret, or redirect URI is missing or empty
- **THEN** the system SHALL fail early with a clear validation error that identifies the missing setting

#### Scenario: Invalid OAuth configuration
- **WHEN** the LinkedIn OAuth configuration is malformed or incompatible with the requested flow
- **THEN** the system SHALL return a safe configuration error without exposing secrets

### Requirement: Safe credential handling
The system SHALL keep LinkedIn OAuth credentials and member identity data out of source control, logs, and tool responses except for the minimal safe metadata already returned by the read-only connectivity check.

#### Scenario: Token exchange succeeds
- **WHEN** the system exchanges an authorization response for LinkedIn credentials
- **THEN** it SHALL store only the credential material needed for continued authorized access and SHALL not log raw tokens

#### Scenario: Tool returns result
- **WHEN** the connectivity tool returns a success or failure result
- **THEN** it SHALL not expose client secrets, access tokens, refresh tokens, or unnecessary private profile data

### Requirement: Stable failure handling for authenticated calls
The system SHALL preserve stable error handling for permission denial, timeout, rate limiting, and generic upstream failures after moving to the ADK-managed OAuth flow.

#### Scenario: Permission denied after authorization
- **WHEN** LinkedIn rejects the authenticated request because the approved scopes or products are insufficient
- **THEN** the system SHALL classify the result as permission denied and preserve a safe diagnostic message

#### Scenario: Upstream failure after authorization
- **WHEN** LinkedIn returns a timeout, rate limit, or other non-success response after the OAuth flow succeeds
- **THEN** the system SHALL normalize the failure into the existing stable error categories
