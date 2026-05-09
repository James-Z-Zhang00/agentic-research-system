from __future__ import annotations

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from agents.base import BaseAgent

_DEFAULT_THRESHOLD = 0.7


class CriticScore(BaseModel):
    factual_consistency: float = Field(ge=0.0, le=1.0)
    hallucination_grounding: float = Field(ge=0.0, le=1.0)
    source_coverage: float = Field(ge=0.0, le=1.0)
    confidence_calibration: float = Field(ge=0.0, le=1.0)
    reasoning: str

    @property
    def average(self) -> float:
        return (
            self.factual_consistency
            + self.hallucination_grounding
            + self.source_coverage
            + self.confidence_calibration
        ) / 4

    def passes(self, threshold: float = _DEFAULT_THRESHOLD) -> bool:
        return self.average >= threshold


class CriticAgent(BaseAgent):
    """LLM-as-Judge quality gate: scores output across 4 dimensions, routes low-confidence to HITL."""

    def __init__(self, llm: ChatAnthropic, threshold: float = _DEFAULT_THRESHOLD) -> None:
        super().__init__(llm, "critic.md")
        self.threshold = threshold

    async def _execute(self, input: dict[str, Any]) -> dict[str, Any]:
        synthesis = input["synthesis"]
        sources = input.get("sources", [])

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(
                content=(
                    f"Evaluate this research output:\n\n{synthesis}\n\n"
                    f"Sources used: {sources}\n\n"
                    "Respond with a JSON CriticScore object."
                )
            ),
        ]
        response = await self.llm.ainvoke(messages)
        score = CriticScore.model_validate_json(str(response.content))
        return {
            "critic_score": score.model_dump(),
            "requires_hitl": not score.passes(self.threshold),
        }

    async def _is_acceptable(self, output: dict[str, Any]) -> bool:
        return "critic_score" in output
