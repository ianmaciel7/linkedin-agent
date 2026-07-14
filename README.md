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

## Development notes

- Use `uv` for dependency management and execution.
- Install the Google ADK runtime with `uv sync`, then run the app with `uv run agents-cli playground` or `uv run agents-cli run "<prompt>"` once credentials are configured.
- Keep repo-local skills under ``.agents/skills/``; use ``./.agents/skills/skill.sh list`` to inspect the pinned set and ``./.agents/skills/skill.sh sync`` to materialize them in a fresh environment.
- Keep changes aligned with the spec-driven workflow before implementation.
- Validate updates with tests and linting as the app grows.

## Planned capabilities

- Profile strength analysis and improvement suggestions.
- Scheduled post drafting and publishing workflows.
- Connection request assistance and outreach sequencing.
- Activity reminders, follow-ups, and lightweight reporting.




