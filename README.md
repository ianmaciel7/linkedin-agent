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
- `openspec/` contains the spec-driven workflow for proposals, specs, and task planning.
- `AGENTS.md` documents the operating standard for contributors and agents.

## LinkedIn API test

The scaffold now includes a small, non-mutating LinkedIn API test tool wired into the ADK agent. It is intended to confirm that credentials and endpoint configuration are valid before building broader LinkedIn workflows.

Required environment variables for the test path:

- `LINKEDIN_ACCESS_TOKEN`: LinkedIn access token for a read-only test call.
- `LINKEDIN_API_TEST_URL`: Optional override for the read-only test endpoint. Defaults to `https://api.linkedin.com/v2/userinfo`.
- `LINKEDIN_API_TIMEOUT_SECONDS`: Optional request timeout in seconds. Defaults to `10`.

Local verification steps:

- `uv run pytest`
- `uv run agents-cli run "Test the configured LinkedIn API connection."`

The test flow returns structured success or failure output and does not create or modify LinkedIn data.

## Development notes

- Use `uv` for dependency management and execution.
- Install the Google ADK runtime with `uv sync`, then run the app with `uv run agents-cli playground` or `uv run agents-cli run "<prompt>"` once credentials are configured.
- Start from `.env.example` for shared variable names; keep local secrets in `.env.local` and production-only values in `.env.prod`.
- Keep repo-local skills under ``.agents/skills/``; use ``./.agents/skills/skill.sh list`` to inspect the pinned set and ``./.agents/skills/skill.sh sync`` to materialize them in a fresh environment.
- Keep changes aligned with the spec-driven workflow before implementation.
- Validate updates with tests and linting as the app grows.

## Planned capabilities

- Profile strength analysis and improvement suggestions.
- Scheduled post drafting and publishing workflows.
- Connection request assistance and outreach sequencing.
- Activity reminders, follow-ups, and lightweight reporting.
