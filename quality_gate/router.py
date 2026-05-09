from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_QUEUE_KEY = "hitl:review_queue"


class HITLQueue:
    """Routes low-confidence Critic outputs to a human review queue (Redis list)."""

    def __init__(self, redis_url: str) -> None:
        self._client = aioredis.from_url(redis_url, decode_responses=True)

    async def enqueue(self, session_id: str, synthesis: str, critic_score: dict[str, Any]) -> None:
        item = {"session_id": session_id, "synthesis": synthesis, "critic_score": critic_score}
        await self._client.lpush(_QUEUE_KEY, json.dumps(item))
        avg = sum(v for k, v in critic_score.items() if isinstance(v, float)) / 4
        logger.info("Session %s → HITL queue (avg_score=%.2f).", session_id, avg)

    async def dequeue(self) -> dict[str, Any] | None:
        raw = await self._client.rpop(_QUEUE_KEY)
        return json.loads(raw) if raw else None

    async def queue_length(self) -> int:
        return await self._client.llen(_QUEUE_KEY)

    async def close(self) -> None:
        await self._client.aclose()


def route_after_critic(state: dict[str, Any]) -> str:
    """LangGraph conditional edge function: passes to 'delivery' or 'hitl'."""
    return "hitl" if state.get("requires_hitl") else "delivery"
