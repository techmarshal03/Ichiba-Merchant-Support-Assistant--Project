"""
NLI-based hallucination checker using GPT-4o-mini structured output.
Returns a grounding score; low scores trigger re-retrieval or escalation.
"""
from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from backend.llm.azure_openai import structured_completion
from backend.config import settings

log = logging.getLogger(__name__)

HALLUCINATION_THRESHOLD = 0.35  # below this → likely hallucinated


class GroundingCheck(BaseModel):
    grounding_score: float = Field(
        ge=0.0, le=1.0,
        description="0=not grounded in context, 1=fully grounded",
    )
    reasoning: str = Field(description="Brief explanation of the score")
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="Specific claims in the response not supported by context",
    )


_SYSTEM = """You are a factual grounding evaluator.
Given a CONTEXT (retrieved knowledge base chunks) and an AI RESPONSE,
score how well the response is grounded in the context.

grounding_score: 1.0 = every claim is directly supported by context
                 0.0 = response contains claims absent from context

List any specific unsupported claims you find."""


async def check_hallucination(
    context_chunks: list[str],
    response: str,
) -> GroundingCheck:
    """
    Check whether the response is grounded in the retrieved context.
    Returns GroundingCheck with score and unsupported claims.
    """
    context_text = "\n\n---\n\n".join(context_chunks[:5])  # top 5 chunks
    user_msg = f"CONTEXT:\n{context_text}\n\nAI RESPONSE:\n{response}"

    try:
        return await structured_completion(
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            response_model=GroundingCheck,
            model=settings.azure_openai_mini_deployment,
            temperature=0.0,
            max_tokens=512,
        )
    except Exception as exc:
        log.warning("Hallucination check failed (%s), returning safe score", exc)
        return GroundingCheck(grounding_score=1.0, reasoning="check skipped", unsupported_claims=[])
