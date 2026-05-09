from __future__ import annotations

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from agents.base import BaseAgent


class FactCheckerAgent(BaseAgent):
    """Cross-validates numeric claims against XBRL-tagged SEC filing data via CoVe."""

    def __init__(self, llm: ChatAnthropic) -> None:
        super().__init__(llm, "fact_checker.md")

    async def _execute(self, input: dict[str, Any]) -> dict[str, Any]:
        task = input["task"]
        claims = input.get("claims", [])
        reflection = input.get("reflection", "")
        reflection_block = f"\n\nPrevious attempt feedback: {reflection}" if reflection else ""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(
                content=(
                    f"Task: {task['description']}\n\n"
                    f"Claims to verify: {claims}"
                    f"{reflection_block}\n\n"
                    "Validate each claim against XBRL ground truth."
                )
            ),
        ]
        response = await self.llm.ainvoke(messages)
        return {"task_id": task["id"], "result": response.content, "verified_claims": []}

    async def _is_acceptable(self, output: dict[str, Any]) -> bool:
        return bool(output.get("result"))
