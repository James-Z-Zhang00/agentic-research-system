from __future__ import annotations

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from agents.base import BaseAgent


class Task(BaseModel):
    id: str
    agent_type: str  # "retrieval" | "analysis" | "fact_checker"
    description: str
    depends_on: list[str] = []
    priority: int = 1


class TaskDAG(BaseModel):
    tasks: list[Task]
    rationale: str


class PlannerAgent(BaseAgent):
    """Decomposes a research goal into a dependency-aware task DAG via ReAct + CoT."""

    def __init__(self, llm: ChatAnthropic) -> None:
        super().__init__(llm, "planner.md")

    async def _execute(self, input: dict[str, Any]) -> dict[str, Any]:
        query = input["query"]
        reflection = input.get("reflection", "")
        reflection_block = f"\n\nPrevious attempt failed — reflection: {reflection}" if reflection else ""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Research goal: {query}{reflection_block}\n\nRespond with a JSON TaskDAG."),
        ]
        response = await self.llm.ainvoke(messages)
        dag = TaskDAG.model_validate_json(str(response.content))
        return {"plan": [t.model_dump() for t in dag.tasks], "rationale": dag.rationale}

    async def _is_acceptable(self, output: dict[str, Any]) -> bool:
        return len(output.get("plan", [])) > 0
