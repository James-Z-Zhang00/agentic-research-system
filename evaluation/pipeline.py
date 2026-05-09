from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EvalCase:
    query: str
    expected_topics: list[str]
    ground_truth_facts: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    case: EvalCase
    synthesis: str
    critic_score: dict[str, Any]
    topic_coverage: float
    fact_accuracy: float

    @property
    def passed(self) -> bool:
        return self.topic_coverage >= 0.8 and self.fact_accuracy >= 0.9


class EvaluationPipeline:
    """End-to-end agent task scoring pipeline — run on every system change."""

    def __init__(self, graph: Any) -> None:
        self._graph = graph

    async def run(self, cases: list[EvalCase]) -> list[EvalResult]:
        results = []
        for case in cases:
            config = {"configurable": {"thread_id": f"eval-{case.query[:30]}"}}
            state = await self._graph.ainvoke(
                {"session_id": "eval", "query": case.query, "agent_results": {}},
                config=config,
            )
            synthesis = state.get("synthesis", "")
            result = EvalResult(
                case=case,
                synthesis=synthesis,
                critic_score=state.get("critic_score", {}),
                topic_coverage=self._topic_coverage(synthesis, case.expected_topics),
                fact_accuracy=self._fact_accuracy(synthesis, case.ground_truth_facts),
            )
            results.append(result)
            logger.info(
                "Eval '%s': coverage=%.2f accuracy=%.2f passed=%s",
                case.query[:50],
                result.topic_coverage,
                result.fact_accuracy,
                result.passed,
            )
        return results

    def _topic_coverage(self, synthesis: str, topics: list[str]) -> float:
        if not topics:
            return 1.0
        return sum(1 for t in topics if t.lower() in synthesis.lower()) / len(topics)

    def _fact_accuracy(self, synthesis: str, facts: list[str]) -> float:
        if not facts:
            return 1.0
        return sum(1 for f in facts if f.lower() in synthesis.lower()) / len(facts)
