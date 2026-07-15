# LinkedIn Agent

An ADK-based LinkedIn assistant focused on profile visibility, engagement, and safe workflow automation.

## Overview

This project is being built in stages. Today, the repository provides a safe read-only LinkedIn foundation:

- LinkedIn OAuth 2.0 login
- OpenID Connect authentication
- read-only `/userinfo` verification
- localhost browser callback support
- environment-based configuration
- unit and integration coverage for the authentication path

It does **not** yet publish posts, send invitations, edit profiles, or automate external LinkedIn actions.

The current implementation is intentionally narrow. Its purpose is to confirm that:

- the LinkedIn OAuth configuration is valid
- the user can authenticate successfully
- the repository can safely call a read-only LinkedIn endpoint
- the agent can expose this capability through a small ADK tool surface

**Current LinkedIn library:** `linkedin-api-client`

## Current Flow

```mermaid
flowchart TD
    A[Start LinkedIn login check] --> B{Credentials available?}
    B -->|Access token| C[Call LinkedIn /userinfo]
    B -->|OAuth config only| D[Start OAuth flow]
    D --> E{Redirect URI uses localhost?}
    E -->|Yes| F[Open browser and wait for callback]
    E -->|No| G[Use ADK-managed OAuth]
    F --> C
    G --> C
    C --> H[Return safe account summary]
```

## Repository Structure

- `app/`: ADK app entry points and agent wiring
- `app/linkedin/`: LinkedIn OAuth and API helpers
- `app/tools/`: tool entry points exposed to the agent
- `tests/`: unit, integration, and eval coverage
- `openspec/`: proposals, specs, and implementation planning

## Configuration

Use `.env.example` as the starting point.

Relevant variables:

- `LINKEDIN_ACCESS_TOKEN`
- `LINKEDIN_CLIENT_ID`
- `LINKEDIN_CLIENT_SECRET`
- `LINKEDIN_REDIRECT_URI`
- `LINKEDIN_API_TEST_URL`
- `LINKEDIN_API_TIMEOUT_SECONDS`
- `LINKEDIN_OAUTH_SCOPES`
- `LINKEDIN_OAUTH_CALLBACK_TIMEOUT_SECONDS`

## Local Verification

- `uv sync`
- `uv run pytest`
- `uv run python -c "import asyncio; from app.tools import run_linkedin_login_service; print(asyncio.run(run_linkedin_login_service()))"`
- `uv run python -c "from app.agent import root_agent; print([tool.__name__ for tool in root_agent.tools])"`

Optional live checks:

- `uv run pytest -m live tests/integration/test_linkedin_api_tool.py`
- `uv run pytest -m live tests/integration/test_linkedin_api_tool.py -q -rs`

## Product Principles

- Keep external LinkedIn actions explicit and reviewable.
- Prefer read-only validation before mutation.
- Require user approval before visible actions such as publishing, commenting, or outreach.
- Avoid undocumented endpoints, scraping, and bulk automation.

## Roadmap

Legend:

- [x] Completed
- [ ] Planned
- 🔒 Requires LinkedIn approval
- 🚫 Not supported by the public LinkedIn API

## Delivery Model

The roadmap is organized into two tracks:

- `Product releases`: user-facing capabilities delivered in sequence
- `Platform enablers`: internal runtime and state foundations required by later releases

## Product Release Path

```mermaid
flowchart LR
    V01[v0.1<br/>Authentication] --> V02[v0.2<br/>Profile Data]
    V02 --> V03[v0.3<br/>Analytics]
    V03 --> V04[v0.4<br/>Publishing]
    V04 --> V05[v0.5<br/>Engagement Copilot]
    V05 --> V06[v0.6<br/>Runtime Services]
    V06 --> V10[v1.0<br/>Outreach]
    V10 --> V11[v1.1<br/>Filters]
    V11 --> V12[v1.2<br/>Automated Cards]
    V12 --> V13[v1.3<br/>Internal Learning]
    V13 --> V14[v1.4<br/>External Post Analysis]
```

## Platform Enablers

```mermaid
flowchart LR
    P06[v0.6<br/>Runtime Services] --> P10[v1.0<br/>Stateful Outreach]
    P10 --> P12[v1.2<br/>Approval Channels]
    P12 --> P13[v1.3<br/>Learning Memory]
```

## Release Summary

| Version | Primary goal | Key deliverables | Depends on |
| --- | --- | --- | --- |
| `v0.1` | Establish safe LinkedIn authentication | OAuth login, OIDC, `/userinfo`, config, tests | None |
| `v0.2` | Build the authenticated identity layer | member URN, profile data, post metadata foundation | `v0.1` |
| `v0.3` | Measure profile and content performance | follower metrics, post analytics, comparisons | `v0.2` |
| `v0.4` | Enable controlled publishing | drafts, preview, publishing, scheduling | `v0.2`, `v0.3` |
| `v0.5` | Support post-level engagement | comment/reaction reading, reply suggestions, approval gates | `v0.4` |
| `v0.6` | Add runtime foundations | session service, memory service, persisted workflow state | `v0.1` |
| `v1.0` | Launch assisted outreach operations | connection targeting, approval queue, limits, history | `v0.5`, `v0.6` |
| `v1.1` | Add reusable audience segmentation | role/company filters, strategic audience selection | `v1.0` |
| `v1.2` | Automate recurring content generation | source-driven cards, approval workflow, traceability | `v0.4`, `v1.1` |
| `v1.3` | Learn from internal performance | growth memory, profile analysis, adaptive recommendations | `v0.3`, `v0.6`, `v1.2` |
| `v1.4` | Learn from external benchmark content | reference post analysis, pattern extraction, knowledge base | `v1.3` |

### v0.1 Authentication Foundation

Primary goal: safe authentication and account validation.

Release outcome: the agent can authenticate a user and validate read-only LinkedIn connectivity end to end.

- [x] OAuth 2.0 login, OpenID Connect, `/userinfo`, environment config, basic error handling, and tests
- [ ] OAuth callback and state validation
- [ ] Secure token storage
- [ ] Token expiration handling

### v0.2 Profile Data

Primary goal: authenticated identity and base profile data.

Release outcome: the system can resolve the authenticated member identity and assemble a stable profile data foundation.

- [x] Retrieve available profile information
- [ ] Build and store the authenticated member URN
- [ ] Import user-supplied profile information
- [ ] Read the authenticated member's posts 🔒
- [ ] Store post metadata and handle unavailable posts

### v0.3 Analytics

Primary goal: profile and post performance measurement.

Release outcome: the product can quantify performance trends and compare content outcomes over time.

- [ ] Follower count and growth history 🔒
- [ ] Post analytics, engagement summary, and comparisons 🔒
- [ ] Reach, reactions, comments, reshares, and historical snapshots 🔒
- [ ] Basic profile completeness analysis and improvement suggestions

### v0.4 Publishing

Primary goal: controlled content creation and publication.

Release outcome: users can draft, preview, approve, and publish posts through a governed workflow.

- [ ] Local drafts and previews
- [ ] User approval before publishing
- [ ] Official API publishing and scheduling
- [ ] Retry, deduplication, and publication history

### v0.5 Engagement Copilot

Primary goal: high-quality engagement support around published content.

Release outcome: the product can assist with post engagement while keeping visible interactions user-approved.

- [ ] Read accessible comments and reactions
- [ ] Identify unanswered comments
- [ ] Suggest replies and reactions
- [ ] Require approval before visible engagement actions
- [ ] Reply through the official API

### v0.6 Runtime Services and Operational Foundation

Primary goal: runtime foundation for stateful automation and approval-driven workflows.

Release outcome: later automation features can rely on configured session and memory services plus persisted workflow state.

- [ ] Define `session service` through environment configuration
- [ ] Define `memory service` through environment configuration
- [ ] Select service types from `.env` for each deployment environment
- [ ] Establish persisted workflow state for approvals and retries
- [ ] Support operational history needed by later outreach and learning flows

### v1.0 Assisted Outreach and Engagement

Primary goal: guided outreach operations with limits and approvals.

Release outcome: the product can suggest and track controlled outreach actions with runtime-backed operational safety.

- [ ] Recommend targets and generate personalized connection messages
- [ ] Queue connection actions for approval
- [ ] Support daily and monthly connection limits
- [ ] Support a configurable comment limit, defaulting to `6`
- [ ] Generate contextual comments for other users' posts
- [ ] Store outreach/comment history and prevent duplicates

### v1.1 Advanced Filters and Audience Selection

Primary goal: reusable targeting and segmentation across workflows.

Release outcome: users can define audience filters once and apply them consistently to outreach and content workflows.

- [ ] Filters by role, company, industry, geography, and seniority
- [ ] Filters for major technology companies and strategic roles
- [ ] Reuse filters across connection, commenting, and publishing flows
- [ ] Save reusable filters
- [ ] Support Premium-related filters when the user provides the source data

### v1.2 Automated Cards and Approval Workflow

Primary goal: recurring card-style content generation from approved sources.

Release outcome: the system can generate repeatable content drafts from trusted sources and route them through approval before publication.

- [ ] Create automated card-style drafts
- [ ] Pull from approved recurring sources such as Google ADK documentation
- [ ] Generate daily or scheduled drafts
- [ ] Send every generated post for approval before publishing
- [ ] Support a planned WhatsApp-based approval flow or equivalent channel
- [ ] Store source-to-post traceability

### v1.3 Internal Learning, Memory, and Profile Analysis

Primary goal: adaptive recommendations based on internal performance and profile evolution.

Release outcome: the product can learn from the user's own history and improve future profile and content recommendations.

- [ ] Learn from the user's best-performing posts 🔒
- [ ] Identify high-engagement patterns 🔒
- [ ] Build reusable post playbooks
- [ ] Maintain a growth memory and adapt recommendations over time
- [ ] Analyze the user's current profile and generate profile improvement tools
- [ ] Turn learned patterns into future content recommendations

### v1.4 External Post Analysis and Knowledge Enrichment

Primary goal: external benchmark analysis to enrich the agent's content knowledge.

Release outcome: the system can extract useful patterns from external reference content and incorporate them into future recommendations.

- [ ] Analyze reference posts supplied by the user
- [ ] Extract structural, thematic, and CTA patterns
- [ ] Compare external patterns with the user's own content history
- [ ] Improve future content recommendations from external analysis
- [ ] Maintain a reusable knowledge base of observed post patterns

### Network Assistant Track

This is a cross-cutting capability track, not a separate release. It should be introduced progressively across `v1.0` and `v1.1`.

- [ ] Analyze a professional selected by the user
- [ ] Recommend `Follow`, `Connect`, or `No action`
- [ ] Generate a personalized connection message
- [ ] Keep invitation sending manual
- [ ] Track suggested manual actions

### Not Planned

- 🚫 People You May Know automation
- 🚫 Automatic bulk connection invitations
- 🚫 Maximum daily connection automation
- 🚫 Browser scraping
- 🚫 Private or undocumented LinkedIn endpoints
- 🚫 Guaranteed automation of LinkedIn Premium search filters
- 🚫 Automatic mass reactions
- 🚫 Generic automatic comments
- 🚫 Unrestricted access to the LinkedIn home feed

## Next Steps

- [ ] Implement OAuth callback and state validation
- [ ] Add secure persisted token handling
- [ ] Add token expiration handling
- [ ] Build and store the authenticated member URN
- [ ] Add profile completeness analysis
