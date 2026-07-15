from __future__ import annotations

import os
from pathlib import Path

import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

_DATASET_PATH = Path(__file__).parent / "datasets" / "basic-dataset.json"


def _has_google_adc() -> bool:
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if credentials_path:
        return Path(credentials_path).expanduser().exists()
    return False


@pytest.mark.live
@pytest.mark.anyio
async def test_agent_evaluator_basic_dataset() -> None:
    if not _has_google_adc():
        pytest.skip(
            "GOOGLE_APPLICATION_CREDENTIALS is required for AgentEvaluator live evals"
        )

    await AgentEvaluator.evaluate(
        agent_module="app.agent",
        eval_dataset_file_path_or_dir=str(_DATASET_PATH),
        num_runs=1,
        print_detailed_results=False,
    )
