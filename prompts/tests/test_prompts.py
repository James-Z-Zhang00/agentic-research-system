"""Prompt regression tests — run on every system prompt change."""
from __future__ import annotations

from pathlib import Path

import pytest

PROMPTS_DIR = Path(__file__).parent.parent
REQUIRED_PROMPTS = ["planner.md", "retrieval.md", "analysis.md", "fact_checker.md", "synthesizer.md", "critic.md"]
MIN_PROMPT_LENGTH = 100


@pytest.mark.parametrize("filename", REQUIRED_PROMPTS)
def test_prompt_exists(filename: str) -> None:
    assert (PROMPTS_DIR / filename).exists(), f"Missing prompt file: {filename}"


@pytest.mark.parametrize("filename", REQUIRED_PROMPTS)
def test_prompt_non_trivial(filename: str) -> None:
    content = (PROMPTS_DIR / filename).read_text()
    assert len(content) >= MIN_PROMPT_LENGTH, f"{filename} is too short — may be a stub"


def test_critic_prompt_contains_dimensions() -> None:
    content = (PROMPTS_DIR / "critic.md").read_text()
    for dimension in ("factual_consistency", "hallucination_grounding", "source_coverage", "confidence_calibration"):
        assert dimension in content, f"critic.md is missing dimension: {dimension}"


def test_planner_prompt_contains_output_schema() -> None:
    content = (PROMPTS_DIR / "planner.md").read_text()
    assert "TaskDAG" in content or '"tasks"' in content, "planner.md must document the TaskDAG output schema"


def test_fact_checker_prompt_mentions_cove() -> None:
    content = (PROMPTS_DIR / "fact_checker.md").read_text()
    assert "CoVe" in content or "Chain-of-Verification" in content, \
        "fact_checker.md must reference the CoVe protocol"
