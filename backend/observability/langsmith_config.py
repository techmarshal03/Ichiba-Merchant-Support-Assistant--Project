"""
LangSmith tracing configuration.
Set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY in env to activate.
"""
from __future__ import annotations

import os
import logging

log = logging.getLogger(__name__)


def configure_langsmith(project_name: str = "ichiba-merchant-support") -> None:
    """Enable LangSmith tracing if API key is available."""
    api_key = os.environ.get("LANGCHAIN_API_KEY")
    if not api_key:
        log.info("LANGCHAIN_API_KEY not set — LangSmith tracing disabled")
        return

    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", project_name)
    os.environ.setdefault("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    log.info("LangSmith tracing enabled → project: %s", project_name)
