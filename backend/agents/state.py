"""
LangGraph agent state — threaded through every node in the graph.
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class MerchantSession(BaseModel):
    """Loaded from Cosmos DB at session start."""
    merchant_id: str
    store_id: str
    store_name: str
    tier: Literal["standard", "gold", "platinum"]
    preferred_language: Literal["ja", "en"]
    open_cases: list[str] = Field(default_factory=list)


class RetrievedChunk(BaseModel):
    id: str
    content: str
    score: float
    domain: str
    language: str
    source_url: str
    section_heading: str
    last_updated: str


class IchibaAgentState(BaseModel):
    """Full LangGraph state schema — threaded through every node."""

    # ── Conversation ──────────────────────────────────────────
    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str
    merchant_session: Optional[MerchantSession] = None

    # ── Language & Intent ─────────────────────────────────────
    detected_language: Literal["ja", "en", "mixed"] = "ja"
    intent: Optional[str] = None
    intent_confidence: float = 0.0
    assigned_agent: Optional[str] = None

    # ── RAG ───────────────────────────────────────────────────
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)

    # ── Generation ────────────────────────────────────────────
    draft_response: Optional[str] = None
    final_response: Optional[str] = None
    hallucination_risk: float = 0.0
    response_confidence: float = 0.0

    # ── Control Flow ──────────────────────────────────────────
    needs_escalation: bool = False
    escalation_reason: Optional[str] = None
    tool_calls_made: list[str] = Field(default_factory=list)
    iteration_count: int = 0
    max_iterations: int = 5

    # ── Observability ─────────────────────────────────────────
    trace_id: str = ""
    node_timings: dict[str, float] = Field(default_factory=dict)
