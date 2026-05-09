from __future__ import annotations

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from agents.base import BaseAgent


class RetrievalAgent(BaseAgent):
    """Fetches information via GraphRAG + web search tools."""

    def __init__(self, llm: ChatAnthropic, tools: list[BaseTool]) -> None:
        super().__init__(llm, "retrieval.md")
        self.tools = tools
        self.llm_with_tools = llm.bind_tools(tools) if tools else llm

    async def _execute(self, input: dict[str, Any]) -> dict[str, Any]:
        task = input["task"]
        reflection = input.get("reflection", "")
        reflection_block = f"\n\nPrevious attempt feedback: {reflection}" if reflection else ""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Task: {task['description']}{reflection_block}"),
        ]
        response = await self.llm_with_tools.ainvoke(messages)
        return {"task_id": task["id"], "result": response.content, "sources": []}

    async def _is_acceptable(self, output: dict[str, Any]) -> bool:
        return bool(output.get("result"))
