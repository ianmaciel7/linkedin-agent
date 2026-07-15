# LinkedIn Agent

An ADK-based assistant for LinkedIn workflow automation and growth support.

## What it helps with

- Improve profile strength with guided profile review and optimization suggestions.
- Schedule auto-posts so content goes out consistently.
- Manage connection workflows, including outreach and follow-up planning.
- Support related growth tasks like content ideas, engagement tracking, and routine admin.

## Project goals

- Keep the agent focused on useful, repeatable LinkedIn actions.
- Make the workflow easy to extend with new tools and tasks.
- Keep the behavior safe, explicit, and reviewable before any outward-facing action.

## Current structure

- `app/` will contain the Google ADK app entry points and agent logic.
- `app/linkedin/` contains read-only LinkedIn API helpers that can be tested without ADK wiring.
- `app/tools/` contains the callable helper used to run the LinkedIn login service.
- `openspec/` contains the spec-driven workflow for proposals, specs, and task planning.
- `AGENTS.md` documents the operating standard for contributors and agents.

## LinkedIn login service

The scaffold now includes a small, non-mutating LinkedIn login service backed by `linkedin-api-client` and ADK OAuth helpers. It is intended to confirm that the user can sign in and that the OAuth configuration is valid before building broader LinkedIn workflows, and it is registered on the ADK root agent as a read-only tool.

Required environment variables for the test path:

- `LINKEDIN_ACCESS_TOKEN`: Optional manual LinkedIn access token for direct test calls outside ADK auth handling.
- `LINKEDIN_CLIENT_ID`: LinkedIn OAuth client ID for ADK-managed auth.
- `LINKEDIN_CLIENT_SECRET`: LinkedIn OAuth client secret for ADK-managed auth.
- `LINKEDIN_REDIRECT_URI`: Redirect URI configured in the LinkedIn app for ADK-managed auth.
- `LINKEDIN_API_TEST_URL`: Optional override for the read-only test endpoint. Defaults to `https://api.linkedin.com/v2/userinfo`.
- `LINKEDIN_API_TIMEOUT_SECONDS`: Optional request timeout in seconds. Defaults to `10`.
- `LINKEDIN_OAUTH_SCOPES`: Optional comma-separated scopes for ADK-managed auth. Defaults to `openid,profile,email`.
- `LINKEDIN_OAUTH_CALLBACK_TIMEOUT_SECONDS`: Optional timeout in seconds for the automatic localhost callback flow. Defaults to `180`.

Local verification steps:

- `uv run pytest`
- `uv run python -c "import asyncio; from app.tools import run_linkedin_login_service; print(asyncio.run(run_linkedin_login_service()))"`
- `uv run python -c "from app.agent import root_agent; print([tool.__name__ for tool in root_agent.tools])"`

Optional live integration test:

- Mark the test with `@pytest.mark.live`
- Provide a valid `LINKEDIN_ACCESS_TOKEN` for the current direct live test path
- Run `uv run pytest -m live tests/integration/test_linkedin_api_tool.py`

Optional OAuth smoke tests:

- Use `uv run pytest -m live tests/integration/test_linkedin_api_tool.py -q -rs` to validate OAuth config and see skip reasons clearly.
- Set `LINKEDIN_AUTH_CODE` to a fresh LinkedIn authorization code if you want to test the full code exchange plus `/userinfo` round-trip.
- Run `uv run python -c "from app.settings import LinkedInApiSettings; from app.linkedin.oauth import run_linkedin_oauth_smoke_test; import os; settings = LinkedInApiSettings.from_env(); print(run_linkedin_oauth_smoke_test(settings, os.environ['LINKEDIN_AUTH_CODE']).to_dict())"` for a direct manual smoke run.
- Run `uv run pytest -m live tests/integration/test_linkedin_api_tool.py -q -rs` with `LINKEDIN_REDIRECT_URI=http://localhost:<porta>/callback` to trigger the automatic browser round-trip. This opens the LinkedIn consent page, waits for the localhost callback, exchanges the code, and calls `/userinfo`.

The test flow returns structured success or failure output and does not create or modify LinkedIn data. Registering it on the ADK agent does not enable posting, messaging, invitations, profile edits, or any other mutating LinkedIn behavior. When the tool runs inside ADK with a `ToolContext`, it prefers ADK-managed OAuth and can request LinkedIn authorization instead of requiring a pasted access token.
When authorization is still pending, the tool also returns a safe `authorization_url` plus short guidance so the agent can show a clickable sign-in link instead of only relying on the default credential prompt UI.

## Development notes

- Use `uv` for dependency management and execution.
- Install the Google ADK runtime with `uv sync`, then run the app with `uv run agents-cli playground` or `uv run agents-cli run "<prompt>"` once credentials are configured.
- VS Code workspace MCP settings live in [`.vscode/mcp.json`](/home/ianma/workspace/linkedin-agent/.vscode/mcp.json) and currently register the `microsoftLearn` server at `https://learn.microsoft.com/api/mcp`.
- The dev environment includes `types-requests` so static checkers can type `requests`-based integrations cleanly.
- Start from `.env.example` for shared variable names; keep local secrets in `.env.local` and production-only values in `.env.prod`.
- Keep repo-local skills under ``.agents/skills/``; use ``./.agents/skills/skill.sh list`` to inspect the pinned set and ``./.agents/skills/skill.sh sync`` to materialize them in a fresh environment.
- Use `.agents/skills/linkedin-api-python-client/` when working on official LinkedIn client integration details such as Rest.li method mapping, OAuth flow selection, or safe usage of `/userinfo`, `/me`, and posting endpoints.
- Keep changes aligned with the spec-driven workflow before implementation.
- Validate updates with tests and linting as the app grows.

## Planned capabilities

- Profile strength analysis and improvement suggestions.
- Scheduled post drafting and publishing workflows.
- Connection request assistance and outreach sequencing.
- Activity reminders, follow-ups, and lightweight reporting.
