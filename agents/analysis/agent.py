from __future__ import annotations

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from agents.base import BaseAgent


class AnalysisAgent(BaseAgent):
    """Reasoning agent; spawns LangGraph subgraphs for deep subtasks (context-isolated)."""

    def __init__(self, llm: ChatAnthropic) -> None:
        super().__init__(llm, "analysis.md")

    async def _execute(self, input: dict[str, Any]) -> dict[str, Any]:
        task = input["task"]
        context = input.get("agent_results", {})
        reflection = input.get("reflection", "")
        reflection_block = f"\n\nPrevious attempt feedback: {reflection}" if reflection else ""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(
                content=(
                    f"Task: {task['description']}\n\n"
                    f"Context from other agents: {context}"
                    f"{reflection_block}"
                )
            ),
        ]
        response = await self.llm.ainvoke(messages)
        return {"task_id": task["id"], "result": response.content}

    async def _is_acceptable(self, output: dict[str, Any]) -> bool:
        return bool(output.get("result"))
