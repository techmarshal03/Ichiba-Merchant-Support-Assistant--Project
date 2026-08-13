"""
Query rewriter: expands merchant queries for better hybrid retrieval.
Uses GPT-4o-mini for low-latency, cost-efficient rewriting.
"""
from __future__ import annotations

import logging
from pydantic import BaseModel

from backend.llm.azure_openai import structured_completion
from backend.config import settings

log = logging.getLogger(__name__)


class RewrittenQuery(BaseModel):
    rewritten: str
    keywords: list[str]


_SYSTEM_JP = (
    "あなたは楽天市場の検索クエリ最適化専門家です。"
    "与えられたユーザーの質問を、知識ベース検索に最適なクエリに書き直してください。"
    "重要なキーワードを抽出し、検索精度が上がるよう表現を明確化してください。"
)
_SYSTEM_EN = (
    "You are a search query optimization expert for Rakuten Ichiba knowledge bases. "
    "Rewrite the user query to improve retrieval precision. "
    "Extract key terms and clarify ambiguous expressions."
)


async def rewrite_query(query: str, language: str = "ja") -> str:
    """Rewrite query for improved RAG retrieval. Falls back to original on error."""
    system = _SYSTEM_JP if language == "ja" else _SYSTEM_EN
    try:
        result = await structured_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": query},
            ],
            response_model=RewrittenQuery,
            model=settings.azure_openai_mini_deployment,
            temperature=0.0,
            max_tokens=256,
        )
        log.debug("Query rewritten: '%s' → '%s'", query[:60], result.rewritten[:60])
        return result.rewritten
    except Exception as exc:
        log.warning("Query rewrite failed (%s), using original", exc)
        return query
