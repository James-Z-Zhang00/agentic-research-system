from __future__ import annotations

import operator
import os
from typing import Annotated, Any, TypedDict

from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph

from agents.analysis.agent import AnalysisAgent
from agents.critic.agent import CriticAgent
from agents.fact_checker.agent import FactCheckerAgent
from agents.planner.agent import PlannerAgent
from agents.retrieval.agent import RetrievalAgent
from agents.synthesizer.agent import SynthesizerAgent
from quality_gate.router import HITLQueue, route_after_critic


class ResearchState(TypedDict):
    session_id: str
    query: str
    plan: list[dict[str, Any]]
    # Annotated with operator.ior so parallel branches merge their dicts rather than overwrite
    agent_results: Annotated[dict[str, Any], operator.ior]
    synthesis: str
    critic_score: dict[str, Any]
    requires_hitl: bool


def build_graph(llm: ChatAnthropic, hitl_queue: HITLQueue) -> StateGraph:
    planner = PlannerAgent(llm)
    retrieval = RetrievalAgent(llm, tools=[])
    analysis = AnalysisAgent(llm)
    fact_checker = FactCheckerAgent(llm)
    synthesizer = SynthesizerAgent(llm)
    critic = CriticAgent(llm, threshold=float(os.getenv("CRITIC_PASS_THRESHOLD", "0.7")))

    async def planner_node(state: ResearchState) -> dict[str, Any]:
        result = await planner.run({"query": state["query"]})
        return {"plan": result["plan"]}

    async def retrieval_node(state: ResearchState) -> dict[str, Any]:
        task = next((t for t in state["plan"] if t["agent_type"] == "retrieval"), None)
        if not task:
            return {"agent_results": {}}
        result = await retrieval.run({"task": task, "query": state["query"]})
        return {"agent_results": {task["id"]: result}}

    async def analysis_node(state: ResearchState) -> dict[str, Any]:
        task = next((t for t in state["plan"] if t["agent_type"] == "analysis"), None)
        if not task:
            return {"agent_results": {}}
        result = await analysis.run(
            {"task": task, "query": state["query"], "agent_results": state["agent_results"]}
        )
        return {"agent_results": {task["id"]: result}}

    async def fact_checker_node(state: ResearchState) -> dict[str, Any]:
        task = next((t for t in state["plan"] if t["agent_type"] == "fact_checker"), None)
        if not task:
            return {"agent_results": {}}
        result = await fact_checker.run({"task": task, "query": state["query"]})
        return {"agent_results": {task["id"]: result}}

    async def synthesizer_node(state: ResearchState) -> dict[str, Any]:
        result = await synthesizer.run(
            {"query": state["query"], "agent_results": state["agent_results"]}
        )
        return {"synthesis": result["synthesis"]}

    async def critic_node(state: ResearchState) -> dict[str, Any]:
        result = await critic.run({"synthesis": state["synthesis"]})
        return {"critic_score": result["critic_score"], "requires_hitl": result["requires_hitl"]}

    async def delivery_node(state: ResearchState) -> dict[str, Any]:
        return {}

    async def hitl_node(state: ResearchState) -> dict[str, Any]:
        await hitl_queue.enqueue(state["session_id"], state["synthesis"], state["critic_score"])
        return {}

    graph = StateGraph(ResearchState)
    for name, fn in [
        ("planner", planner_node),
        ("retrieval", retrieval_node),
        ("analysis", analysis_node),
        ("fact_checker", fact_checker_node),
        ("synthesizer", synthesizer_node),
        ("critic", critic_node),
        ("delivery", delivery_node),
        ("hitl", hitl_node),
    ]:
        graph.add_node(name, fn)

    graph.add_edge(START, "planner")
    # Fan-out: retrieval / analysis / fact_checker run in parallel
    for agent in ("retrieval", "analysis", "fact_checker"):
        graph.add_edge("planner", agent)
        graph.add_edge(agent, "synthesizer")
    graph.add_edge("synthesizer", "critic")
    graph.add_conditional_edges(
        "critic", route_after_critic, {"delivery": "delivery", "hitl": "hitl"}
    )
    graph.add_edge("delivery", END)
    graph.add_edge("hitl", END)

    return graph


async def create_app(postgres_url: str, llm: ChatAnthropic, hitl_queue: HITLQueue) -> Any:
    """Compile graph with AsyncPostgresSaver for fault-tolerant, resumable checkpointing."""
    graph = build_graph(llm, hitl_queue)
    async with AsyncPostgresSaver.from_conn_string(postgres_url) as checkpointer:
        await checkpointer.setup()
        return graph.compile(checkpointer=checkpointer)
