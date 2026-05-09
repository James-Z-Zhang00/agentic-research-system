from __future__ import annotations

import logging
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from memory.episodic import EpisodicMemory
from memory.semantic import SemanticMemory
from memory.working import WorkingMemory

logger = logging.getLogger(__name__)

_CONSOLIDATION_PROMPT = """You are consolidating a research session into long-term memory.

Given the session's intermediate results, produce a concise structured summary that:
1. Preserves key findings and verified facts
2. Notes unresolved questions or low-confidence claims
3. Strips ephemeral task state and internal agent artifacts

Respond with a single coherent research summary."""


class MemoryConsolidator:
    """Runs at session teardown: compresses Redis working memory → PostgreSQL episodic + pgvector."""

    def __init__(
        self,
        llm: ChatAnthropic,
        working: WorkingMemory,
        episodic: EpisodicMemory,
        semantic: SemanticMemory,
    ) -> None:
        self._llm = llm
        self._working = working
        self._episodic = episodic
        self._semantic = semantic

    async def consolidate(self, session_id: str) -> str | None:
        """Return the new episode_id, or None if the session had no data."""
        session_data = await self._working.get_session(session_id)
        if not session_data:
            logger.info("Session %s has no working memory to consolidate.", session_id)
            return None

        query = str(session_data.get("query", "unknown"))
        messages = [
            SystemMessage(content=_CONSOLIDATION_PROMPT),
            HumanMessage(content=f"Session data:\n{session_data}"),
        ]
        response = await self._llm.ainvoke(messages)
        consolidated = str(response.content)

        episode_id = await self._episodic.save(
            session_id=session_id,
            query=query,
            synthesis=consolidated,
            critic_score=session_data.get("critic_score"),
        )
        await self._semantic.store(episode_id=episode_id, query=query)
        await self._working.delete_session(session_id)

        logger.info("Consolidated session %s → episode %s.", session_id, episode_id)
        return episode_id
