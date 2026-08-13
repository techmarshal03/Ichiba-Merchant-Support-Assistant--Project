"""
LangGraph AsyncPostgresSaver checkpointer factory.
Manages conversation state persistence per merchant session thread.
"""
from __future__ import annotations

import logging

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from backend.config import settings

log = logging.getLogger(__name__)


async def create_checkpointer() -> AsyncPostgresSaver:
    """
    Create and set up the PostgreSQL checkpointer.
    Called once at application startup via FastAPI lifespan.
    """
    checkpointer = AsyncPostgresSaver.from_conn_string(settings.postgres_dsn)
    await checkpointer.setup()  # creates checkpoint tables if not exist
    log.info("LangGraph PostgreSQL checkpointer initialized")
    return checkpointer


def make_config(session_id: str) -> dict:
    """Build LangGraph run config for a given merchant session."""
    return {
        "configurable": {
            "thread_id": session_id,
        }
    }
