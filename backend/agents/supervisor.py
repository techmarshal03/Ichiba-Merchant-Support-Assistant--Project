"""
Supervisor nodes: language detection, intent classification, routing,
confidence evaluation, hallucination check, response formatting, escalation.
"""
from __future__ import annotations
import re
from enum import Enum
from typing import Optional
from langdetect import detect_langs, LangDetectException
from pydantic import BaseModel
from backend.agents.state import IchibaAgentState
from backend.config import settings


# ── Language Detector ─────────────────────────────────────────

async def language_detector_node(state: IchibaAgentState, config: dict) -> dict:
    """Three-layer: CJK heuristic → langdetect → merchant profile fallback."""
    text = state.messages[-1].content
    has_cjk   = any(0x3000 <= ord(c) <= 0x9FFF for c in text)
    has_latin = any(c.isascii() and c.isalpha() for c in text)
    try:
        langs      = detect_langs(text)
        top        = langs[0]
        lang_code  = "ja" if top.lang == "ja" else "en"
        confidence = top.prob
    except LangDetectException:
        lang_code, confidence = "ja", 0.5

    if has_cjk and has_latin and confidence < 0.85:
        lang_code = "mixed"
    elif confidence < 0.70 and state.merchant_session:
        lang_code = state.merchant_session.preferred_language

    return {"detected_language": lang_code}


# ── Intent Classifier ─────────────────────────────────────────

class Intent(str, Enum):
    store_setup        = "store_setup"
    product_listing    = "product_listing"
    order_management   = "order_management"
    payment_settlement = "payment_settlement"
    campaign           = "campaign"
    api_technical      = "api_technical"
    policy_compliance  = "policy_compliance"
    analytics          = "analytics"

class IntentClassification(BaseModel):
    intent: Intent
    confidence: float
    secondary_intent: Optional[Intent] = None

INTENT_PROMPT = """You are an intent classifier for Rakuten Ichiba merchant support.
Language: {language}
Classify into ONE: store_setup|product_listing|order_management|payment_settlement|campaign|api_technical|policy_compliance|analytics
Return JSON only: {{"intent": str, "confidence": float}}"""

async def intent_classifier_node(state: IchibaAgentState, config: dict) -> dict:
    from backend.llm.azure_openai import azure_client
    response = await azure_client.beta.chat.completions.parse(
        model="gpt4o-mini-ichiba",
        messages=[
            {"role": "system", "content": INTENT_PROMPT.format(language=state.detected_language)},
            {"role": "user",   "content": state.messages[-1].content},
        ],
        response_format=IntentClassification,
        temperature=0.0, max_tokens=64,
    )
    result = response.choices[0].message.parsed
    return {"intent": result.intent.value, "intent_confidence": result.confidence}


# ── Router ────────────────────────────────────────────────────

INTENT_TO_AGENT = {
    "store_setup":        "store",
    "product_listing":    "store",
    "order_management":   "order",
    "payment_settlement": "payment",
    "campaign":           "campaign",
    "api_technical":      "api",
    "policy_compliance":  "policy",
    "analytics":          "store",
}

async def router_node(state: IchibaAgentState, config: dict) -> dict:
    return {"iteration_count": state.iteration_count + 1}

def route_to_specialist(state: IchibaAgentState) -> str:
    if state.iteration_count > state.max_iterations:
        return "escalate"
    return INTENT_TO_AGENT.get(state.intent or "", "store")


# ── Confidence Evaluator ──────────────────────────────────────

async def confidence_evaluator_node(state: IchibaAgentState, config: dict) -> dict:
    return {}  # confidence already set by hallucination_checker; gate reads state directly

def confidence_gate(state: IchibaAgentState) -> str:
    if state.iteration_count > state.max_iterations:
        return "escalate"
    if state.response_confidence >= settings.CONFIDENCE_THRESHOLD:
        return "pass"
    if state.iteration_count < 2:
        return "retry"
    return "escalate"


# ── Hallucination Checker ─────────────────────────────────────

class GroundingCheck(BaseModel):
    grounding_score: float
    unsupported_claims: list[str]

GROUNDING_PROMPT = """Evaluate whether RESPONSE is supported by CONTEXT.
Score 0.0 (hallucinated) → 1.0 (fully grounded).
CONTEXT:\n{context}\n\nRESPONSE:\n{response}
Return JSON: {{"grounding_score": float, "unsupported_claims": [str]}}"""

async def hallucination_checker_node(state: IchibaAgentState, config: dict) -> dict:
    from backend.llm.azure_openai import azure_client
    if not state.retrieved_chunks:
        return {"hallucination_risk": 0.95, "response_confidence": 0.05}
    context = "\n\n".join(c.content for c in state.retrieved_chunks)[:5000]
    result = await azure_client.beta.chat.completions.parse(
        model="gpt4o-mini-ichiba",
        messages=[{"role": "user", "content": GROUNDING_PROMPT.format(
            context=context, response=state.draft_response)}],
        response_format=GroundingCheck,
        temperature=0.0, max_tokens=256,
    )
    check = result.choices[0].message.parsed
    return {
        "hallucination_risk":  1.0 - check.grounding_score,
        "response_confidence": check.grounding_score,
    }

def hallucination_gate(state: IchibaAgentState) -> str:
    return "risky" if state.hallucination_risk > settings.HALLUCINATION_THRESHOLD else "safe"


# ── Response Formatter ────────────────────────────────────────

ESCALATION_CTA = {
    "ja": "\n\n---\n💡 さらに詳しいご確認が必要な場合は、マーチャントサポートセンターにお問い合わせください。",
    "en": "\n\n---\n💡 For further assistance, please contact the Merchant Support Center.",
    "mixed": "\n\n---\n💡 Please contact the Merchant Support Center / マーチャントサポートセンターにご連絡ください。",
}

async def response_formatter_node(state: IchibaAgentState, config: dict) -> dict:
    lang  = state.detected_language
    draft = state.draft_response or ""
    if state.citations:
        sep = "\n\n【参照文書】\n" if lang == "ja" else "\n\n**Sources:**\n"
        draft += sep + "\n".join(f"- {c}" for c in state.citations)
    if state.response_confidence < 0.80:
        draft += ESCALATION_CTA.get(lang, ESCALATION_CTA["en"])
    return {"final_response": draft}


# ── Escalation ────────────────────────────────────────────────

async def escalation_node(state: IchibaAgentState, config: dict) -> dict:
    """Push to Azure Service Bus escalation queue and return a holding message."""
    import logging
    logger = logging.getLogger(__name__)
    reason = state.escalation_reason or "low_confidence"
    logger.warning("Escalating session %s — reason: %s", state.session_id, reason)
    # In production: publish to Service Bus queue
    # await service_bus_client.send_message(EscalationMessage(...))
    msg = (
        "申し訳ございません。このご質問はサポート担当者に引き継ぎます。"
        if state.detected_language == "ja"
        else "We're connecting you with a support specialist. Someone will be in touch shortly."
    )
    return {"final_response": msg, "needs_escalation": True}
