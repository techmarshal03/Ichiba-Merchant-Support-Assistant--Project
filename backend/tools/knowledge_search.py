"""Knowledge base search tool — wraps hybrid_rag_retrieve for LangChain ReAct agents."""
from __future__ import annotations

from langchain_core.tools import tool

from backend.rag.retriever import hybrid_rag_retrieve


@tool
async def knowledge_search_tool(query: str, domain: str = "store", language: str = "ja") -> str:
    """
    Search the Ichiba merchant knowledge base using hybrid RAG (vector + BM25).
    Returns the top relevant document excerpts.

    Args:
        query: Merchant's question or search terms
        domain: Knowledge domain (store/order/payment/campaign/api/policy)
        language: Query language (ja/en)
    """
    chunks = await hybrid_rag_retrieve(query=query, domain=domain, language=language, top_k=5)
    if not chunks:
        return "No relevant knowledge base articles found for this query."
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[{i}] {chunk.content}\n(Source: {chunk.source}, Score: {chunk.score:.3f})")
    return "\n\n".join(parts)
