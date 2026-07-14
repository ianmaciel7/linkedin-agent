---
name: linkedin-agent-cli-deploy
description: >
  Lightweight deployment extension for this repository. Use this when the task
  is to prepare or explain deployment of the linkedin-agent ADK app with the
  Google agents CLI. Prefer this skill for repo-local deploy commands, dry runs,
  and simple dev deployment guidance.
metadata:
  author: OpenAI Codex
  license: Apache-2.0
  version: 0.1.0
  extends: google-agents-cli-deploy
  requires:
    bins:
      - agents-cli
      - uv
---

# LinkedIn Agent Deploy Extension

This skill narrows the general `google-agents-cli-deploy` guidance to this
repository.

## Scope

Use this skill when:

- The user wants a simple deploy command for `linkedin-agent`
- The user wants a dry-run deployment check before a real deploy
- The user wants repo-local deployment helper scripts

Use `google-agents-cli-deploy` for the full production deployment reference and
Google Cloud platform details.

## Project assumptions

- App package: `app`
- Project name: `linkedin-agent`
- Dependency management: `uv`
- Expected validation before deploy:
  - `uv run pytest`
  - `uv run ruff check .`

## Local helper script

This extension provides:

- `scripts/deploy_dev.sh`

The script:

- validates common inputs
- builds an `agents-cli deploy` command for this repo
- uses `agents-cli` when available and falls back to `uvx --from google-agents-cli agents-cli`
- loads deployment values from `.env.local` or `.env` by default, or a custom file via `--env-file`
- lets explicit CLI flags override env-file values
- defaults to `--dry-run`
- only executes the deploy when `--execute` is passed

## Recommended workflow

1. Run validation checks.
2. Run the deploy helper in dry-run mode.
3. Review project, region, and service account values.
4. Ask for explicit human approval before a real deploy.
5. Re-run with `--execute` only after approval.

## Example

```bash
./.agents/skills/linkedin-agent-cli-deploy/scripts/deploy_dev.sh \
  --project-id my-dev-project \
  --region us-central1 \
  --service-account agent-runtime@my-dev-project.iam.gserviceaccount.com
```

Using env values instead:

```bash
./.agents/skills/linkedin-agent-cli-deploy/scripts/deploy_dev.sh --env-file .env.local
```

To execute for real:

```bash
./.agents/skills/linkedin-agent-cli-deploy/scripts/deploy_dev.sh \
  --project-id my-dev-project \
  --region us-central1 \
  --service-account agent-runtime@my-dev-project.iam.gserviceaccount.com \
  --execute
```
