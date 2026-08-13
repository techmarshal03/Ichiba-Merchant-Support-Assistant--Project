"""
Hybrid RAG retriever: dense vector + BM25 sparse → RRF → Cohere reranker.
"""
from __future__ import annotations
import logging
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.identity.aio import WorkloadIdentityCredential
from backend.agents.state import RetrievedChunk
from backend.config import settings
from backend.rag.embedder import get_embedding
from backend.rag.reranker import cohere_rerank
from backend.rag.query_rewriter import rewrite_query

logger = logging.getLogger(__name__)

_search_client: SearchClient | None = None

def get_search_client() -> SearchClient:
    global _search_client
    if _search_client is None:
        _search_client = SearchClient(
            endpoint=settings.AZURE_SEARCH_ENDPOINT,
            index_name=settings.AZURE_SEARCH_INDEX,
            credential=WorkloadIdentityCredential(),
        )
    return _search_client


async def hybrid_rag_retrieve(
    query: str,
    domain: str,
    language: str,
    merchant_tier: str,
    top_k: int = 8,
) -> list[RetrievedChunk]:
    """
    Full Hybrid RAG pipeline:
    1. Query rewriting (normalize JP variants, expand abbreviations)
    2. Dense + BM25 hybrid search via Azure AI Search semantic ranker (RRF internally)
    3. Cohere cross-encoder reranking
    4. Return top-5 RetrievedChunk objects
    """
    rewritten = await rewrite_query(query, language)
    embedding = await get_embedding(rewritten)

    # OData filter: domain + language + tier
    tier_clause = f"merchant_tier eq '{merchant_tier}' or merchant_tier eq 'all'"
    lang_clause = f"language eq '{language}' or language eq 'bilingual'"
    odata_filter = f"(domain eq '{domain}') and ({lang_clause}) and ({tier_clause})"

    vector_query = VectorizedQuery(
        vector=embedding,
        k_nearest_neighbors=top_k * 2,
        fields="content_vector",
    )

    client = get_search_client()
    results = await client.search(
        search_text=rewritten,
        vector_queries=[vector_query],
        filter=odata_filter,
        query_type="semantic",
        semantic_configuration_name="ichiba-semantic-config",
        top=top_k,
        select=["id", "content", "domain", "language",
                "source_url", "section_heading", "last_updated"],
    )

    raw_chunks = [
        {"id": r["id"], "content": r["content"], "metadata": r}
        async for r in results
    ]

    if not raw_chunks:
        logger.warning("No chunks retrieved for domain=%s lang=%s query=%s",
                       domain, language, query[:60])
        return []

    reranked = await cohere_rerank(query=rewritten, documents=raw_chunks, top_n=5)

    return [
        RetrievedChunk(
            id=c["id"],
            content=c["content"],
            score=c.get("relevance_score", 0.0),
            domain=c["metadata"]["domain"],
            language=c["metadata"]["language"],
            source_url=c["metadata"]["source_url"],
            section_heading=c["metadata"]["section_heading"],
            last_updated=c["metadata"].get("last_updated", ""),
        )
        for c in reranked
    ]


async def ping_search() -> None:
    """Health check for Azure AI Search."""
    client = get_search_client()
    await client.get_document_count()
