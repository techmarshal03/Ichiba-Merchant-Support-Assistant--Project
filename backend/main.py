"""
Ichiba Merchant Support Assistant — FastAPI Application Entry Point
"""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from backend.agents.graph import build_ichiba_graph
from backend.config import settings
from backend.guardrails.injection_guard import PromptInjectionGuard
from backend.guardrails.pii_protector import PIIProtector
from backend.memory.checkpointer import create_checkpointer
from backend.memory.merchant_profile import MerchantProfileRepository
from backend.observability.metrics import LATENCY, QUERIES
from backend.observability.tracing import setup_tracing
from backend.security.auth import authenticate_merchant
from backend.security.secrets import SecretsManager
from backend.agents.state import MerchantSession

logger = logging.getLogger(__name__)


# ── Request / Response models ──────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"


# ── Lifespan (startup / shutdown) ─────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize all services at startup, clean up on shutdown."""
    logger.info("Starting Ichiba Merchant Support Agent v%s", settings.APP_VERSION)

    setup_tracing()
    secrets_mgr = SecretsManager()
    app.state.secrets          = secrets_mgr
    app.state.checkpointer     = await create_checkpointer()
    app.state.graph            = build_ichiba_graph(app.state.checkpointer)
    app.state.merchant_repo    = MerchantProfileRepository(secrets_mgr)
    app.state.injection_guard  = PromptInjectionGuard()
    app.state.pii_protector    = PIIProtector()

    logger.info("All services initialized. Ready to serve merchants.")
    yield

    # Shutdown
    await app.state.checkpointer.pool.close()
    logger.info("Ichiba Merchant Support Agent shut down cleanly.")


# ── FastAPI application ────────────────────────────────────────

app = FastAPI(
    title="Ichiba Merchant Support Agent",
    description="Multilingual multi-agent AI platform for Rakuten Ichiba merchants",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Chat endpoint (SSE streaming) ─────────────────────────────

@app.post("/v1/chat")
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    merchant: MerchantSession = Depends(authenticate_merchant),
):
    """
    Send a merchant message and receive a streaming SSE response.

    Merchant tier (standard / gold / platinum) controls tool access.
    Language is auto-detected (JP primary, EN secondary).
    """
    # 1. Prompt injection guard
    is_injection, reason = await app.state.injection_guard.check(request.message)
    if is_injection:
        raise HTTPException(status_code=400, detail=f"Invalid input: {reason}")

    config = {
        "configurable": {
            "thread_id": f"{merchant.merchant_id}:{request.session_id}",
            "checkpoint_ns": "ichiba_v1",
        }
    }

    async def event_stream():
        try:
            async for chunk in app.state.graph.astream(
                {
                    "messages": [HumanMessage(content=request.message)],
                    "session_id": request.session_id,
                    "merchant_session": merchant,
                },
                config=config,
                stream_mode="values",
            ):
                if chunk.get("final_response"):
                    payload = json.dumps(
                        {"content": chunk["final_response"], "done": True},
                        ensure_ascii=False,
                    )
                    yield f"data: {payload}\n\n"

        except Exception as e:
            logger.error("Graph execution error: %s", e, exc_info=True)
            error_payload = json.dumps(
                {"error": "Internal error. Escalating to support.", "done": True},
                ensure_ascii=False,
            )
            yield f"data: {error_payload}\n\n"

        finally:
            yield "data: [DONE]\n\n"

        # Background: log masked conversation for analytics
        background_tasks.add_task(
            _log_conversation,
            merchant_id=merchant.merchant_id,
            message=app.state.pii_protector.mask(request.message),
            session_id=request.session_id,
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── Health endpoints ───────────────────────────────────────────

@app.get("/health/live", response_model=HealthResponse)
async def liveness():
    """Kubernetes liveness probe."""
    return HealthResponse(status="ok")


@app.get("/health/ready", response_model=HealthResponse)
async def readiness():
    """Kubernetes readiness probe — checks critical dependencies."""
    from backend.memory.checkpointer import ping_postgres
    from backend.memory.semantic_cache import ping_redis
    from backend.rag.retriever import ping_search

    checks = await asyncio.gather(
        ping_postgres(), ping_redis(), ping_search(),
        return_exceptions=True,
    )
    if any(isinstance(c, Exception) for c in checks):
        failed = [["postgres", "redis", "search"][i] for i, c in enumerate(checks)
                  if isinstance(c, Exception)]
        raise HTTPException(503, detail=f"Dependencies unhealthy: {failed}")

    return HealthResponse(status="ready")


# ── Background tasks ───────────────────────────────────────────

async def _log_conversation(merchant_id: str, message: str, session_id: str) -> None:
    """Log PII-masked conversation for analytics (fire-and-forget)."""
    logger.info(
        "conversation",
        extra={
            "merchant_id": merchant_id,
            "session_id": session_id,
            "message_preview": message[:100],
        },
    )
