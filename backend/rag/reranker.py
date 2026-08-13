"""
Cohere multilingual-v3 reranker for hybrid RAG post-processing.
"""
from __future__ import annotations

import logging

import cohere

from backend.config import settings

log = logging.getLogger(__name__)

_client: cohere.AsyncClient | None = None


def _get_client() -> cohere.AsyncClient:
    global _client
    if _client is None:
        _client = cohere.AsyncClient(api_key=settings.cohere_api_key)
    return _client


async def rerank(
    query: str,
    documents: list[str],
    top_n: int = 5,
) -> list[int]:
    """
    Return indices of top_n documents sorted by Cohere rerank score.
    Uses multilingual-v3 model suitable for JP + EN mixed content.
    """
    if not documents:
        return []

    client = _get_client()
    response = await client.rerank(
        model="rerank-multilingual-v3.0",
        query=query,
        documents=documents,
        top_n=min(top_n, len(documents)),
    )
    return [r.index for r in response.results]
