from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from langchain_anthropic import ChatAnthropic

from api.schemas import HITLItem, ResearchRequest, ResearchResponse
from graph import create_app
from memory.consolidator import MemoryConsolidator
from memory.episodic import EpisodicMemory
from memory.semantic import SemanticMemory
from memory.working import WorkingMemory
from quality_gate.router import HITLQueue

_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    llm = ChatAnthropic(model="claude-opus-4-7", api_key=os.environ["ANTHROPIC_API_KEY"])
    working = WorkingMemory(os.environ["REDIS_URL"])
    episodic = EpisodicMemory(os.environ["POSTGRES_URL"])
    semantic = SemanticMemory(os.environ["POSTGRES_URL"], embedder=None)  # wire embedder
    hitl_queue = HITLQueue(os.getenv("HITL_QUEUE_URL", os.environ["REDIS_URL"]))
    consolidator = MemoryConsolidator(llm, working, episodic, semantic)

    await episodic.initialize()
    graph = await create_app(os.environ["POSTGRES_URL"], llm, hitl_queue)

    _state.update(graph=graph, working=working, consolidator=consolidator, hitl_queue=hitl_queue)
    yield
    await working.close()
    await hitl_queue.close()


app = FastAPI(title="Multiagent Research System", lifespan=lifespan)


@app.post("/research", response_model=ResearchResponse)
async def run_research(request: ResearchRequest) -> ResearchResponse:
    session_id = request.session_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    final_state = await _state["graph"].ainvoke(
        {"session_id": session_id, "query": request.query, "agent_results": {}},
        config=config,
    )
    await _state["consolidator"].consolidate(session_id)

    return ResearchResponse(
        session_id=session_id,
        synthesis=final_state["synthesis"],
        critic_score=final_state["critic_score"],
        requires_hitl=final_state["requires_hitl"],
    )


@app.get("/hitl/queue/length")
async def hitl_queue_length() -> dict[str, int]:
    return {"length": await _state["hitl_queue"].queue_length()}


@app.post("/hitl/dequeue", response_model=HITLItem | None)
async def dequeue_hitl() -> HITLItem | None:
    item = await _state["hitl_queue"].dequeue()
    return HITLItem(**item) if item else None
