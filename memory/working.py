from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis


class WorkingMemory:
    """Per-session short-term memory backed by Redis. TTL-bounded; consolidated at session teardown."""

    def __init__(self, redis_url: str, ttl_seconds: int = 3600) -> None:
        self._client = aioredis.from_url(redis_url, decode_responses=True)
        self._ttl = ttl_seconds

    def _key(self, session_id: str, field: str) -> str:
        return f"session:{session_id}:{field}"

    async def set(self, session_id: str, field: str, value: Any) -> None:
        await self._client.setex(self._key(session_id, field), self._ttl, json.dumps(value))

    async def get(self, session_id: str, field: str) -> Any | None:
        raw = await self._client.get(self._key(session_id, field))
        return json.loads(raw) if raw else None

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """Return all fields for a session as a flat dict."""
        keys = await self._client.keys(self._key(session_id, "*"))
        result: dict[str, Any] = {}
        for key in keys:
            field = key.split(":", 2)[-1]
            raw = await self._client.get(key)
            if raw:
                result[field] = json.loads(raw)
        return result

    async def delete_session(self, session_id: str) -> None:
        keys = await self._client.keys(self._key(session_id, "*"))
        if keys:
            await self._client.delete(*keys)

    async def close(self) -> None:
        await self._client.aclose()
