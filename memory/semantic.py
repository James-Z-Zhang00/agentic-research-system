from __future__ import annotations

import uuid
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Text, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from memory.episodic import Base


class ResearchEmbedding(Base):
    __tablename__ = "research_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    episode_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    query = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    metadata_ = Column("metadata", JSONB, default=dict)


class SemanticMemory:
    """Similarity-based recall of prior research via pgvector; queried at session start."""

    def __init__(self, postgres_url: str, embedder: Any) -> None:
        self._engine = create_async_engine(postgres_url)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)
        self._embedder = embedder  # any LangChain Embeddings object

    async def initialize(self) -> None:
        async with self._engine.begin() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await conn.run_sync(Base.metadata.create_all)

    async def store(self, episode_id: str, query: str, metadata: dict[str, Any] | None = None) -> None:
        embedding = await self._embedder.aembed_query(query)
        async with self._session_factory() as session:
            record = ResearchEmbedding(
                episode_id=uuid.UUID(episode_id),
                query=query,
                embedding=embedding,
                metadata_=metadata or {},
            )
            session.add(record)
            await session.commit()

    async def recall(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Return the top_k most similar prior research episodes."""
        embedding = await self._embedder.aembed_query(query)
        async with self._session_factory() as session:
            result = await session.execute(
                select(ResearchEmbedding)
                .order_by(ResearchEmbedding.embedding.l2_distance(embedding))
                .limit(top_k)
            )
            return [
                {"episode_id": str(r.episode_id), "query": r.query, "metadata": r.metadata_}
                for r in result.scalars()
            ]
