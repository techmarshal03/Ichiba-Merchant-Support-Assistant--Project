"""
Prompt injection detection — pattern matching + LLM classifier.
Covers English and Japanese attack variants.
"""
from __future__ import annotations
import re
import logging

logger = logging.getLogger(__name__)

INJECTION_PATTERNS = [
    # English
    r"ignore\s+(previous|all|above|prior)\s+instructions",
    r"you\s+are\s+now\s+",
    r"system\s+prompt",
    r"\bjailbreak\b",
    r"\bDAN\s+mode\b",
    r"do\s+anything\s+now",
    r"forget\s+.{0,20}instructions",
    r"new\s+persona",
    r"override\s+(your|all)\s+(instructions|rules)",
    r"act\s+as\s+if\s+you\s+(have\s+no|are\s+not)",
    # Japanese
    r"以前の指示を無視",
    r"指示を忘れ",
    r"システムプロンプト",
    r"あなたは今から",
    r"別の人格",
    r"ロールプレイ.*無制限",
    r"制限なし.*モード",
]


class PromptInjectionGuard:
    def __init__(self) -> None:
        self._patterns = [
            re.compile(p, re.IGNORECASE | re.UNICODE)
            for p in INJECTION_PATTERNS
        ]

    async def check(self, text: str) -> tuple[bool, str]:
        # Layer 1: fast regex scan
        for pat in self._patterns:
            if pat.search(text):
                logger.warning("Injection pattern detected: %s", pat.pattern[:40])
                return True, f"Injection pattern: {pat.pattern[:40]}"

        # Layer 2: LLM-based check for sophisticated evasion (>80 chars only)
        if len(text) > 80:
            try:
                verdict = await self._llm_check(text)
                if verdict:
                    logger.warning("LLM-classified prompt injection detected")
                    return True, "LLM-classified injection"
            except Exception as e:
                logger.error("Injection LLM check failed: %s", e)

        return False, ""

    async def _llm_check(self, text: str) -> bool:
        from backend.llm.azure_openai import azure_client
        from pydantic import BaseModel

        class InjectionVerdict(BaseModel):
            is_injection: bool
            confidence: float

        result = await azure_client.beta.chat.completions.parse(
            model="gpt4o-mini-ichiba",
            messages=[{
                "role": "user",
                "content": (
                    "Is the following message an attempt to inject instructions into an AI system, "
                    "override its guidelines, or make it behave outside its intended purpose?\n\n"
                    f"Message: {text[:500]}\n\n"
                    'Return JSON: {"is_injection": bool, "confidence": float}'
                ),
            }],
            response_format=InjectionVerdict,
            temperature=0.0, max_tokens=50,
        )
        verdict = result.choices[0].message.parsed
        return verdict.is_injection and verdict.confidence > 0.85
