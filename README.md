# agentic-research-system

An autonomous multi-agent research system for deep, multi-step financial analysis. Decomposes complex research goals into dependency-aware task graphs, executes them through specialized agents with self-correction loops, and delivers quality-gated, fact-checked outputs — with a three-tier memory system that accumulates institutional knowledge across sessions.

> **Status:** Active development

---

## Overview

Single-hop RAG retrieval handles straightforward queries well. It breaks down on complex, multi-step research tasks — comparing revenue trends across competitors, synthesizing findings from multiple filings, or cross-validating claims against multiple data sources simultaneously.

This system handles those tasks autonomously. A Planner agent decomposes the goal into a task DAG, specialized agents execute each step in parallel where dependencies allow, a Critic agent quality-gates every output before delivery, and a three-tier memory system ensures agents build on prior research rather than starting from scratch each session.

Operates standalone or as a composable service callable by [graph-rag-finance-assistant](../graph-rag-finance-assistant) when a query exceeds single-hop retrieval capability.

---

## Key Capabilities

### Multi-Agent Orchestration
- **Plan-and-Execute architecture** via LangGraph on LangChain — Planner decomposes natural-language goals into dependency-aware task DAGs
- **ReAct-style reasoning** for step-by-step task decomposition before acting
- **Reflexion-based self-correction** — each agent reflects on its own output and retries on failure
- **Dynamic subagent spawning** via LangGraph subgraphs for context-isolated execution of deep subtasks
- Agent roles: `Planner`, `Retrieval`, `Analysis`, `Fact-Checker`, `Synthesizer`, `Critic`
- Versioned, regression-tested system prompts per agent role — treated as code artifacts

### Three-Tier Agent Memory
- **Short-term working memory** (Redis) — per-session intermediate results and active task state
- **Long-term episodic memory** (PostgreSQL) — research findings and completed analyses persisted across sessions
- **Semantic memory** (pgvector) — similarity-based recall of prior relevant research at session start
- LLM-driven memory consolidation compresses expiring context into long-term storage before session teardown

### HITL Quality Gate + Critic Agent
- **LLM-as-Judge Critic** scores every agent output across 4 dimensions: factual consistency, hallucination grounding, source coverage, confidence calibration
- **HITL review queue** automatically escalates low-confidence outputs to human review before delivery
- **Chain-of-Verification (CoVe)** pattern — Fact-Checker cross-validates numeric claims against XBRL-tagged ground truth from SEC filings
- Catches hallucinations at every inter-agent boundary before they compound downstream

### System Observability & Resilience
- **LangSmith** for per-agent invocation tracing — latency, token usage, success/failure rates per node
- **OpenTelemetry** for cross-service distributed tracing
- **LangGraph checkpointing** — fault-tolerant, resumable workflows via `AsyncPostgresSaver`
- Circuit breakers with exponential backoff on all external API dependencies
- Automated end-to-end evaluation pipeline runs on every system change

---

## Tech Stack

| Layer | Technologies |
|---|---|
| Agent Orchestration | LangGraph, LangChain |
| Observability | LangSmith, OpenTelemetry |
| Memory | Redis (short-term), PostgreSQL + pgvector (long-term + semantic) |
| Quality Gate | LLM-as-Judge, Chain-of-Verification (CoVe), HITL queue |
| Resilience | LangGraph checkpointing, Tenacity (circuit breakers) |
| API Framework | FastAPI |
| Task Queue | Celery + Redis |
| Containerization | Docker, docker-compose |

---

## Architecture

```
         Trigger (query / scheduled / P1 delegation)
                          │
                          ▼
                      Planner Agent
               (ReAct + CoT task decomposition)
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        Retrieval     Analysis    Fact-Checker
          Agent         Agent       Agent
        (GraphRAG)   (reasoning)  (XBRL validation)
              └───────────┬───────────┘
                          ▼
                    Synthesizer Agent
                   (structured output)
                          │
                          ▼
              ┌─────────────────────┐
              │  LLM-as-Judge Critic │
              │  4-dimension scoring │
              └──────────┬──────────┘
                   pass  │  fail (low confidence)
                    ▼    │    ▼
                Delivery  HITL Review Queue
```

---

## Memory Architecture

```
Session Start
  │
  ▼
pgvector semantic search ──► retrieve relevant prior research
  │
  ▼
Redis working memory ──────► active task state + intermediate results
  │
  ▼  (context threshold reached)
PostgreSQL episodic store ─► LLM consolidation + long-term write
```

---

## Project Structure

```
agentic-research-system/
├── agents/
│   ├── planner/          # ReAct + CoT task decomposition
│   ├── retrieval/        # GraphRAG + web search tools
│   ├── analysis/         # Reasoning + subagent spawning
│   ├── fact_checker/     # XBRL cross-validation
│   ├── synthesizer/      # Structured output generation
│   └── critic/           # LLM-as-Judge quality scoring
├── memory/               # Three-tier memory system (Redis + PostgreSQL + pgvector)
├── quality_gate/         # HITL queue + confidence threshold routing
├── observability/        # LangSmith + OpenTelemetry setup
├── evaluation/           # End-to-end agent task scoring pipeline
├── prompts/              # Versioned agent system prompts
│   └── tests/            # Prompt regression test suites
├── api/                  # FastAPI service interface (P1 integration)
├── docker-compose.yml
└── .env.example
```

---

## Related Projects

- **[graph-rag-finance-assistant](../graph-rag-finance-assistant)** — Production GraphRAG system for SEC financial filings; delegates complex multi-step research tasks to this system
- **[multimodal-ragops-platform](../multimodal-ragops-platform)** — RAGOps evaluation and fine-tuning platform; RAGAS-derived scoring patterns reused by the Critic agent

---

## License

MIT
