"""RMS API documentation search tool."""
from __future__ import annotations

from langchain_core.tools import tool

from backend.rag.retriever import hybrid_rag_retrieve


@tool
async def rms_api_docs_tool(query: str, language: str = "en") -> str:
    """
    Search RMS API documentation for endpoint specs, parameters, and code examples.

    Args:
        query: API-related question (e.g. 'how to update inventory via API')
        language: Language for results (ja/en)
    """
    chunks = await hybrid_rag_retrieve(
        query=query, domain="api", language=language, top_k=3
    )
    if not chunks:
        return "No API documentation found. Refer to https://api.rms.rakuten.co.jp/documentation"
    return "\n\n".join(f"[{i+1}] {c.content}" for i, c in enumerate(chunks))
