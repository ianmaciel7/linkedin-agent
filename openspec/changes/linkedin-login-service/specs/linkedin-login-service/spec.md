## ADDED Requirements

### Requirement: ADK-managed LinkedIn OAuth
The system SHALL acquire LinkedIn authorization for the OAuth service through ADK-managed OAuth rather than requiring a manually pasted access token for normal operation.

#### Scenario: Authorization required
- **WHEN** the OAuth service runs without a valid cached credential
- **THEN** the system SHALL request LinkedIn authorization through the ADK execution context

#### Scenario: Authorization reused
- **WHEN** the OAuth service runs with a valid cached credential for the current session
- **THEN** the system SHALL reuse that credential and skip another consent prompt

### Requirement: Validated OAuth configuration
The system SHALL validate the LinkedIn OAuth configuration before starting authorization and SHALL fail early when required settings are missing or invalid.

#### Scenario: Missing OAuth client setting
- **WHEN** a required LinkedIn OAuth setting such as client ID, client secret, or redirect URI is missing or empty
- **THEN** the system SHALL return a clear validation error that identifies the missing setting

#### Scenario: Invalid OAuth configuration
- **WHEN** the LinkedIn OAuth configuration is malformed or incompatible with the requested login flow
- **THEN** the system SHALL return a safe configuration error without exposing secrets

### Requirement: Safe credential handling
The system SHALL keep LinkedIn credentials and member identity data out of source control, logs, and tool responses except for minimal safe metadata needed to confirm login success.

#### Scenario: Token exchange succeeds
- **WHEN** the system exchanges an authorization response for LinkedIn credentials
- **THEN** it SHALL store only the credential material needed for continued authorized access and SHALL not log raw tokens

#### Scenario: Login result returned
- **WHEN** the OAuth service returns a success or failure result
- **THEN** it SHALL not expose client secrets, access tokens, refresh tokens, or unnecessary private profile data

### Requirement: Read-only login boundary
The system SHALL use the OAuth service only to establish authenticated access and confirm connectivity.

#### Scenario: Successful authenticated login
- **WHEN** the user completes authorization and the configured read-only LinkedIn endpoint is reachable
- **THEN** the system SHALL return a structured success result for the OAuth service

#### Scenario: Read-only boundary preserved
- **WHEN** the OAuth service completes successfully
- **THEN** the system SHALL not publish posts, send messages, send invitations, or modify profile data

### Requirement: Stable failure handling
The system SHALL normalize permission denial, timeout, rate limiting, and other upstream failures after the OAuth flow begins.

#### Scenario: Permission denied after authorization
- **WHEN** LinkedIn rejects the authenticated request because the approved scopes or products are insufficient
- **THEN** the system SHALL classify the result as permission denied and preserve a safe diagnostic message

#### Scenario: Upstream failure after authorization
- **WHEN** LinkedIn returns a timeout, rate limit, or other non-success response after the OAuth flow succeeds
- **THEN** the system SHALL normalize the failure into a stable error category
