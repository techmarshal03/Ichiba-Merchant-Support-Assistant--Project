"""
Prometheus metrics for the Ichiba support assistant.
Tracks latency, token usage, cache hits, escalations, and agent routing.
"""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, start_http_server

from backend.config import settings

# ---------------------------------------------------------------------------
# Metrics definitions
# ---------------------------------------------------------------------------

REQUEST_LATENCY = Histogram(
    "ichiba_request_latency_seconds",
    "End-to-end request latency",
    labelnames=["domain", "language", "tier"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

LLM_TOKENS_TOTAL = Counter(
    "ichiba_llm_tokens_total",
    "Total LLM tokens consumed",
    labelnames=["model", "direction"],  # direction: input | output
)

CACHE_HIT = Counter(
    "ichiba_semantic_cache_hits_total",
    "Semantic cache hits",
    labelnames=["domain"],
)

CACHE_MISS = Counter(
    "ichiba_semantic_cache_misses_total",
    "Semantic cache misses",
    labelnames=["domain"],
)

ESCALATION_TOTAL = Counter(
    "ichiba_escalations_total",
    "Queries escalated to human support",
    labelnames=["domain", "reason"],  # reason: low_confidence | hallucination | explicit
)

AGENT_ROUTING = Counter(
    "ichiba_agent_routing_total",
    "Intent-to-agent routing decisions",
    labelnames=["domain"],
)

HALLUCINATION_SCORE = Histogram(
    "ichiba_hallucination_score",
    "Hallucination grounding scores",
    labelnames=["domain"],
    buckets=[0.1, 0.2, 0.35, 0.5, 0.7, 0.85, 1.0],
)

ACTIVE_SESSIONS = Gauge(
    "ichiba_active_sessions",
    "Currently active merchant sessions",
)

INJECTION_BLOCKED = Counter(
    "ichiba_injection_blocked_total",
    "Prompt injection attempts blocked",
    labelnames=["method"],  # method: regex | llm
)


def start_metrics_server() -> None:
    """Start Prometheus metrics HTTP server on configured port."""
    port = settings.metrics_port
    start_http_server(port)
