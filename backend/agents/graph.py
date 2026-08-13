"""
LangGraph StateGraph — Ichiba Merchant Support multi-agent graph.
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from backend.agents.state import IchibaAgentState
from backend.agents.supervisor import (
    language_detector_node,
    intent_classifier_node,
    router_node,
    route_to_specialist,
    confidence_evaluator_node,
    confidence_gate,
    hallucination_checker_node,
    hallucination_gate,
    response_formatter_node,
    escalation_node,
)
from backend.agents.specialists.base import make_specialist_agent

SPECIALIST_DOMAINS = ["store", "order", "payment", "campaign", "api", "policy"]


def build_ichiba_graph(checkpointer: AsyncPostgresSaver) -> StateGraph:
    """
    Build and compile the full LangGraph multi-agent graph.

    Topology:
      language_detector → intent_classifier → router
        → [specialist]_agent → confidence_evaluator
          → hallucination_checker → response_formatter → END
          ↘ escalation → END
    """
    graph = StateGraph(IchibaAgentState)

    # ── Register nodes ────────────────────────────────────────
    graph.add_node("language_detector",     language_detector_node)
    graph.add_node("intent_classifier",     intent_classifier_node)
    graph.add_node("router",                router_node)
    graph.add_node("confidence_evaluator",  confidence_evaluator_node)
    graph.add_node("hallucination_checker", hallucination_checker_node)
    graph.add_node("response_formatter",    response_formatter_node)
    graph.add_node("escalation",            escalation_node)

    for domain in SPECIALIST_DOMAINS:
        graph.add_node(f"{domain}_agent", make_specialist_agent(domain))

    # ── Entry point ───────────────────────────────────────────
    graph.set_entry_point("language_detector")

    # ── Linear pre-routing ────────────────────────────────────
    graph.add_edge("language_detector",  "intent_classifier")
    graph.add_edge("intent_classifier",  "router")

    # ── Conditional routing to specialist ────────────────────
    graph.add_conditional_edges(
        "router",
        route_to_specialist,
        {
            **{d: f"{d}_agent" for d in SPECIALIST_DOMAINS},
            "escalate": "escalation",
        },
    )

    # ── All specialists → confidence evaluator ────────────────
    for domain in SPECIALIST_DOMAINS:
        graph.add_edge(f"{domain}_agent", "confidence_evaluator")

    # ── Confidence gate ───────────────────────────────────────
    graph.add_conditional_edges(
        "confidence_evaluator",
        confidence_gate,
        {
            "pass":     "hallucination_checker",
            "retry":    "router",
            "escalate": "escalation",
        },
    )

    # ── Hallucination gate ────────────────────────────────────
    graph.add_conditional_edges(
        "hallucination_checker",
        hallucination_gate,
        {
            "safe":  "response_formatter",
            "risky": "escalation",
        },
    )

    graph.add_edge("response_formatter", END)
    graph.add_edge("escalation",         END)

    return graph.compile(checkpointer=checkpointer)
