"""
Production Azure OpenAI client with Workload Identity auth,
primary + fallback region, exponential backoff, and streaming.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Type, TypeVar

import tenacity
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncAzureOpenAI
from openai import APIStatusError, APIConnectionError, RateLimitError
from pydantic import BaseModel

from backend.config import settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

_credential: DefaultAzureCredential | None = None


def _get_credential() -> DefaultAzureCredential:
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential


def _make_client(endpoint: str) -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=lambda: _get_token_sync(),
        api_version="2024-10-01-preview",
    )


def _get_token_sync() -> str:
    """Sync wrapper used by openai's token_provider signature."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_get_token_async())


async def _get_token_async() -> str:
    cred = _get_credential()
    token = await cred.get_token("https://cognitiveservices.azure.com/.default")
    return token.token


# Primary and fallback clients (lazy-initialized)
_primary_client: AsyncAzureOpenAI | None = None
_fallback_client: AsyncAzureOpenAI | None = None


def get_primary_client() -> AsyncAzureOpenAI:
    global _primary_client
    if _primary_client is None:
        _primary_client = _make_client(settings.azure_openai_endpoint)
    return _primary_client


def get_fallback_client() -> AsyncAzureOpenAI:
    global _fallback_client
    if _fallback_client is None:
        _fallback_client = _make_client(settings.azure_openai_fallback_endpoint)
    return _fallback_client


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

_RETRYABLE = (RateLimitError, APIConnectionError)

retry_policy = tenacity.retry(
    retry=tenacity.retry_if_exception_type(_RETRYABLE),
    wait=tenacity.wait_exponential(multiplier=1, min=1, max=30),
    stop=tenacity.stop_after_attempt(4),
    before_sleep=tenacity.before_sleep_log(log, logging.WARNING),
)


# ---------------------------------------------------------------------------
# Structured output (parse)
# ---------------------------------------------------------------------------

@retry_policy
async def structured_completion(
    messages: list[dict[str, Any]],
    response_model: Type[T],
    *,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> T:
    """
    Call GPT-4o with structured outputs.  Falls back to secondary region on
    APIStatusError (5xx) from primary.
    """
    deployment = model or settings.azure_openai_deployment
    clients = [get_primary_client(), get_fallback_client()]

    last_exc: Exception | None = None
    for client in clients:
        try:
            result = await client.beta.chat.completions.parse(
                model=deployment,
                messages=messages,
                response_format=response_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return result.choices[0].message.parsed  # type: ignore[return-value]
        except APIStatusError as exc:
            if exc.status_code >= 500:
                log.warning("Primary region error %s, trying fallback", exc.status_code)
                last_exc = exc
                continue
            raise
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Streaming completion
# ---------------------------------------------------------------------------

@retry_policy
async def stream_completion(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    system_prompt: str | None = None,
) -> AsyncIterator[str]:
    """Yield text deltas from a streaming GPT-4o response."""
    deployment = model or settings.azure_openai_deployment
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages

    client = get_primary_client()
    async with client.chat.completions.stream(
        model=deployment,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    ) as stream:
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

@retry_policy
async def embed_text(text: str) -> list[float]:
    """Return 3072-dim embedding using text-embedding-3-large."""
    client = get_primary_client()
    resp = await client.embeddings.create(
        input=text,
        model=settings.azure_openai_embedding_deployment,
        dimensions=3072,
    )
    return resp.data[0].embedding


async def embed_batch(texts: list[str], batch_size: int = 16) -> list[list[float]]:
    """Embed multiple texts in parallel batches."""
    results: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = await asyncio.gather(*[embed_text(t) for t in batch])
        results.extend(embeddings)
    return results
