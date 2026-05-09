from __future__ import annotations

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from agents.base import BaseAgent


class SynthesizerAgent(BaseAgent):
    """Merges all agent results into a structured research output."""

    def __init__(self, llm: ChatAnthropic) -> None:
        super().__init__(llm, "synthesizer.md")

    async def _execute(self, input: dict[str, Any]) -> dict[str, Any]:
        query = input["query"]
        agent_results = input["agent_results"]
        reflection = input.get("reflection", "")
        reflection_block = f"\n\nPrevious attempt feedback: {reflection}" if reflection else ""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(
                content=(
                    f"Original research goal: {query}\n\n"
                    f"Agent findings:\n{agent_results}"
                    f"{reflection_block}"
                )
            ),
        ]
        response = await self.llm.ainvoke(messages)
        return {"synthesis": response.content}

    async def _is_acceptable(self, output: dict[str, Any]) -> bool:
        synthesis = output.get("synthesis", "")
        return isinstance(synthesis, str) and len(synthesis) > 100
