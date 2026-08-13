"""
Semantic cache using Redis + vector similarity.
Cache key = cosine similarity >= 0.95 against stored query embeddings.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional

import numpy as np
import redis.asyncio as aioredis

from backend.config import settings
from backend.llm.azure_openai import embed_text

log = logging.getLogger(__name__)

# TTLs by domain (seconds)
DOMAIN_TTL: dict[str, int] = {
    "store":    3600 * 6,   # 6h – store config changes infrequently
    "order":    60 * 5,     # 5m – order status is time-sensitive
    "payment":  3600 * 24,  # 24h – settlement docs stable
    "campaign": 3600 * 2,   # 2h – campaign info can change
    "api":      3600 * 12,  # 12h – API docs stable
    "policy":   3600 * 24,  # 24h – policy docs stable
}

SIMILARITY_THRESHOLD = 0.95
CACHE_PREFIX = "ichiba:semantic:"


class SemanticCache:
    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None

    @property
    def redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.redis_connection_string,
                decode_responses=False,
            )
        return self._redis

    async def get(self, query: str, domain: str) -> Optional[str]:
        """Return cached response if a similar query exists, else None."""
        query_vec = await embed_text(query)
        pattern = f"{CACHE_PREFIX}{domain}:*"
        keys = [k async for k in self.redis.scan_iter(pattern, count=100)]

        for key in keys:
            raw = await self.redis.get(key)
            if raw is None:
                continue
            entry = json.loads(raw)
            stored_vec = entry["embedding"]
            sim = _cosine(query_vec, stored_vec)
            if sim >= SIMILARITY_THRESHOLD:
                log.debug("Cache HIT  sim=%.3f domain=%s", sim, domain)
                return entry["response"]

        log.debug("Cache MISS domain=%s", domain)
        return None

    async def set(self, query: str, domain: str, response: str) -> None:
        """Store query + response in cache with domain-appropriate TTL."""
        query_vec = await embed_text(query)
        key_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        key = f"{CACHE_PREFIX}{domain}:{key_hash}"
        ttl = DOMAIN_TTL.get(domain, 3600)

        payload = json.dumps({"embedding": query_vec, "response": response})
        await self.redis.setex(key, ttl, payload.encode())


def _cosine(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0
