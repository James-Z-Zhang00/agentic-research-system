from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, String, Text, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class ResearchEpisode(Base):
    __tablename__ = "research_episodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String, nullable=False, index=True)
    query = Column(Text, nullable=False)
    synthesis = Column(Text, nullable=False)
    critic_score = Column(JSONB, nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class EpisodicMemory:
    """Long-term research findings persisted across sessions in PostgreSQL."""

    def __init__(self, postgres_url: str) -> None:
        self._engine = create_async_engine(postgres_url, echo=False)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    async def initialize(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def save(
        self,
        session_id: str,
        query: str,
        synthesis: str,
        critic_score: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        async with self._session_factory() as session:
            episode = ResearchEpisode(
                session_id=session_id,
                query=query,
                synthesis=synthesis,
                critic_score=critic_score,
                metadata_=metadata or {},
            )
            session.add(episode)
            await session.commit()
            return str(episode.id)

    async def get_by_session(self, session_id: str) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ResearchEpisode)
                .where(ResearchEpisode.session_id == session_id)
                .order_by(ResearchEpisode.created_at)
            )
            return [
                {
                    "id": str(ep.id),
                    "query": ep.query,
                    "synthesis": ep.synthesis,
                    "created_at": ep.created_at.isoformat(),
                }
                for ep in result.scalars()
            ]
