# AGENTS.md

## Project overview

This repository contains `linkedin-agent`, a Python application built with Google's Agent Development Kit (ADK). Keep the implementation aligned with current ADK conventions and treat this file as the project-wide operating guide for coding agents.

The repository is still being scaffolded. Do not claim that commands, dependencies, integrations, or deployment targets exist until their files are present. When introducing them, update this file and `README.md` in the same change.

## Intended structure

Use the standard ADK application layout:

```text
app/
  __init__.py        # exports `app`
  agent.py           # tools, root_agent, and App definition
tests/
  unit/
  integration/
  eval/
    datasets/
    eval_config.yaml
openspec/
  specs/              # canonical, accepted product behavior
  changes/            # proposed changes and implementation tasks
  config.yaml         # OpenSpec project configuration
pyproject.toml        # metadata, Python version, dependencies, and tool config
uv.lock              # reproducible dependency lock
```

- Define `root_agent` in `app/agent.py` with `google.adk.agents.Agent`.
- Wrap it in `google.adk.apps.App`; the app name must match the package directory name (`app`).
- Export `app` from `app/__init__.py`.
- Keep tool implementations small and typed. A tool's docstring is part of its contract with the model and must clearly state when to call it, its inputs, and its result.
- Separate LinkedIn/domain logic from ADK wiring as the codebase grows. Do not put all business logic in `agent.py`.

## Environment and commands

Target Python 3.11 or newer and use `uv` for dependency management. Once `pyproject.toml` exists, use:

```bash
uv sync
uv run agents-cli playground
uv run agents-cli run "<prompt>"
uv run pytest
uv run ruff check .
uv run ruff format --check .
openspec validate --all
uv run python -c "from app.settings import LinkedInApiSettings; from app.linkedin.oauth import run_linkedin_oauth_smoke_test; import os; settings = LinkedInApiSettings.from_env(); print(run_linkedin_oauth_smoke_test(settings, os.environ['LINKEDIN_AUTH_CODE']).to_dict())"
```

Use the commands actually defined by the repository if they later differ. Do not hand-edit `uv.lock`; regenerate it with `uv` when dependencies change. Do not deploy or run cloud-changing commands unless the user explicitly requests it.

Workspace MCP configuration lives in [`.vscode/mcp.json`](/home/ianma/workspace/linkedin-agent/.vscode/mcp.json) and currently registers the `microsoftLearn` HTTP server at `https://learn.microsoft.com/api/mcp`.

Repo-local skills that must be shared across environments live under ``.agents/skills/``. When the repository adds versioned skill sources, use ``./.agents/skills/skill.sh list`` to inspect the lock file and ``./.agents/skills/skill.sh sync`` to materialize the pinned skills into the workspace copy.

## OpenSpec workflow

`openspec/specs/` is the source of truth for accepted behavior. `openspec/changes/` contains proposed deltas until they are implemented, validated, and archived.

- For a new capability, breaking change, architecture change, or ambiguous multi-file change, create an OpenSpec change before implementation.
- Read the relevant canonical specs and active change artifacts before editing code.
- Keep `proposal.md` focused on why and scope, delta specs on testable behavior, `design.md` on technical decisions, and `tasks.md` on verifiable implementation steps.
- Express requirements with MUST or SHALL and include Given/When/Then scenarios.
- Small bug fixes that restore already-specified behavior may proceed directly, but update the canonical spec if the behavior was undocumented.
- Mark tasks complete only after the corresponding implementation and verification are complete.
- Run `openspec validate --all` before handoff. Archive a change only after implementation is complete and the user requests or approves archival.
- Do not edit generated OpenSpec agent integrations manually; refresh them with `openspec update` after upgrading OpenSpec or changing supported tools. In this repository, the generated integration files live under `.agents/`.
- Any new skill added for this project must also have an equivalent checked-in version under `.agents/skills/`.
## Implementation conventions

- Add type annotations to public functions and tool inputs/outputs.
- Prefer explicit data models for structured inputs and outputs.
- Keep prompts readable and version-controlled; avoid assembling large prompts through scattered string concatenation.
- Use async functions for network-bound operations when the underlying client supports them.
- Inject clients and external services so unit tests can replace them with fakes.
- Keep callbacks, tools, session/state handling, and orchestration concerns in separate modules once they become non-trivial.
- Use comments to explain decisions, not obvious mechanics.
- Avoid unrelated refactors and preserve existing public behavior unless a specification requires a change.

## Testing and evaluation

Every behavior change must include proportionate verification:

- Unit-test deterministic domain logic and tool validation without calling real models or external services.
- Integration-test ADK wiring, tool selection boundaries, and service adapters with controlled fakes or test credentials.
- Add or update ADK evaluation cases for changes to instructions, routing, tool use, or response quality.
- Cover success, invalid input, permission denial, rate limiting, timeout, and upstream failure where relevant.
- Run the smallest relevant checks while iterating, then the full local test and lint suite before handoff.
- Never weaken assertions or evaluation thresholds merely to make a change pass.

## LinkedIn and external-action safety

- Treat profile data, messages, contacts, tokens, cookies, and generated drafts as sensitive.
- Never commit credentials or personal data. Document required variables in `.env.example` using placeholders.
- Require explicit user confirmation immediately before publishing a post, sending a message or invitation, modifying a profile, deleting data, or performing another externally visible action.
- Drafting and previewing are distinct from execution. Default to a preview when intent is ambiguous.
- Make mutating tools idempotent where possible and prevent retries from duplicating posts or messages.
- Respect platform terms, API permissions, rate limits, and privacy requirements. Do not add scraping, evasion, spam, bulk outreach, or deceptive engagement behavior.
- Log operational metadata, not secrets, access tokens, private message bodies, or unnecessary personal data.

## Configuration and dependencies

- Read configuration from environment variables through one validated settings layer.
- Fail early with a useful error when required configuration is missing.
- Pin and lock dependencies. Prefer official Google ADK and provider SDKs over custom protocol implementations.
- Keep type-checker support dependencies such as `types-requests` in sync with runtime imports when static analysis covers third-party libraries without bundled stubs.
- When adding a variable, update the settings model, `.env.example`, tests, and README documentation together.

## Change workflow

1. Read this file, `README.md`, relevant files in `openspec/specs/` and `openspec/changes/`, and any more specific nested `AGENTS.md` before editing.
2. Inspect the current code and tests; do not assume the intended scaffold is already implemented.
3. Make the smallest coherent change that satisfies the request.
4. Add or update tests and evaluations.
5. Run relevant formatting, linting, tests, and evaluation checks.
6. Summarize changed behavior, verification performed, and any remaining risk or unverified external dependency.

Do not modify generated artifacts, lockfiles, deployment state, or unrelated user changes unless the task requires it.




