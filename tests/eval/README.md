# Eval Guide

This directory follows the Google Agent Platform and `agents-cli` eval pattern
for local ADK agent evaluation.

## Required files

- `datasets/basic-dataset.json`: scaffold-default dataset used by `agents-cli eval generate`
- `eval_config.yaml`: default metrics used by `agents-cli eval grade`
- `test_agent_evaluator.py`: optional pytest wrapper for running the same dataset through `google.adk.evaluation.AgentEvaluator`

## Official local workflow

1. Define eval cases in `datasets/basic-dataset.json`.
2. Keep prompts realistic and user-facing.
3. Run inference:

```bash
agents-cli eval generate
```

4. Grade traces:

```bash
agents-cli eval grade
```

5. Inspect the generated results in `artifacts/grade_results/`.
6. Fix agent instructions, tool descriptions, routing, or code.
7. Re-run eval and compare results when iterating.

## Optional pytest-style eval entrypoint

If you want an ADK-native pytest entrypoint similar to:

```python
from google.adk.evaluation.agent_evaluator import AgentEvaluator

await AgentEvaluator.evaluate(...)
```

this repository also includes `tests/eval/test_agent_evaluator.py`.

Run it explicitly because it is marked `live` and requires Google ADC:

```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/adc.json \
uv run pytest -m live tests/eval/test_agent_evaluator.py
```

Use this as a lightweight wrapper around the existing eval dataset. Keep the
`agents-cli eval generate` / `agents-cli eval grade` workflow as the primary
path for grading, comparison, and iterative analysis.

## Google-recommended practices

- Start with a small dataset and expand after cases pass consistently.
- Prefer realistic user prompts over implementation notes.
- Keep each eval case focused on one user-visible task or one important failure mode.
- Keep the default no-flag workflow working by maintaining `tests/eval/datasets/basic-dataset.json`.
- Use multi-turn metrics for agent goal completion and tool quality.
- Keep safety evaluation enabled for auth, privacy, and read-only boundary behavior.
- Analyze failures before changing prompts or code.
- Do not lower thresholds or remove cases just to make scores pass.
- Use simulated datasets when you need cold-start scenario generation:

```bash
agents-cli eval dataset synthesize
```

- Use compare after meaningful changes:

```bash
agents-cli eval compare <old_results.json> <new_results.json>
```

- Use optimize only when prompt optimization is explicitly desired, because it
  is expensive and long-running.

## Recommended metrics for this repository

The default `eval_config.yaml` uses:

- `multi_turn_task_success`
- `final_response_quality`
- `multi_turn_tool_use_quality`
- `safety`

These align well with this repository's current auth-heavy, user-visible,
tool-driven agent behavior.

This metric set follows the Google-recommended pattern of combining:

- goal completion
- final response quality
- tool-use quality
- safety

## Operational notes

- `agents-cli eval generate` requires the repository to be recognized as an
  agent project and requires Google ADC to be configured.
- If generation fails before inference, fix the local project or CLI setup.
- If generation fails during inference, investigate ADC, model access, runtime
  errors, or tool behavior.

## Rules

- Keep the dataset filename as `basic-dataset.json` unless there is a strong reason to require `--dataset`.
- Prefer adding new eval cases to the existing default dataset while the repo has only one main user-facing capability area.
- Use `agents-cli eval compare` after meaningful changes instead of judging improvements by memory.
- Use `agents-cli eval dataset synthesize` when manual scenario authoring is slowing down coverage growth.
- Use `agents-cli eval optimize` only for explicit prompt-optimization work, not as a substitute for fixing routing, tools, or code.
