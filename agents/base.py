from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
MAX_REFLEXION_RETRIES = 3


class BaseAgent(ABC):
    """Base class implementing the Reflexion self-correction loop."""

    def __init__(self, llm: BaseChatModel, prompt_file: str) -> None:
        self.llm = llm
        self.system_prompt = (PROMPTS_DIR / prompt_file).read_text()

    @abstractmethod
    async def _execute(self, input: dict[str, Any]) -> dict[str, Any]:
        """Single execution pass."""
        ...

    @abstractmethod
    async def _is_acceptable(self, output: dict[str, Any]) -> bool:
        """Quality check — return True if output meets acceptance criteria."""
        ...

    async def _reflect(self, output: dict[str, Any]) -> str:
        response = await self.llm.ainvoke(
            f"The following output failed quality checks. What went wrong and how should it be improved?\n\n{output}"
        )
        return str(response.content)

    async def run(self, input: dict[str, Any]) -> dict[str, Any]:
        """Run with Reflexion: self-correct up to MAX_REFLEXION_RETRIES times."""
        current_input = input
        output: dict[str, Any] = {}
        for attempt in range(MAX_REFLEXION_RETRIES):
            output = await self._execute(current_input)
            if await self._is_acceptable(output):
                return output
            if attempt < MAX_REFLEXION_RETRIES - 1:
                reflection = await self._reflect(output)
                logger.warning(
                    "%s quality check failed (attempt %d/%d). Reflecting.",
                    self.__class__.__name__,
                    attempt + 1,
                    MAX_REFLEXION_RETRIES,
                )
                current_input = {**current_input, "reflection": reflection}
        logger.error("%s exhausted reflexion retries. Returning best effort.", self.__class__.__name__)
        return output
