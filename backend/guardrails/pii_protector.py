"""
PII detection and masking using Microsoft Presidio.
Includes JP-specific recognizers: phone numbers, merchant IDs, email.
"""
from __future__ import annotations

import logging
import re

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom JP recognizers
# ---------------------------------------------------------------------------

_JP_PHONE = PatternRecognizer(
    supported_entity="JP_PHONE_NUMBER",
    patterns=[
        Pattern("JP mobile", r"0[789]0[-\s]?\d{4}[-\s]?\d{4}", 0.9),
        Pattern("JP landline", r"0\d{1,4}[-\s]?\d{1,4}[-\s]?\d{4}", 0.8),
    ],
)

_MERCHANT_ID = PatternRecognizer(
    supported_entity="RAKUTEN_MERCHANT_ID",
    patterns=[
        Pattern("Merchant ID", r"\b[a-zA-Z0-9_]{4,20}\b(?=\s*店|store)", 0.8),
    ],
)

# ---------------------------------------------------------------------------
# Engine setup
# ---------------------------------------------------------------------------

_analyzer = AnalyzerEngine()
_analyzer.registry.add_recognizer(_JP_PHONE)
_analyzer.registry.add_recognizer(_MERCHANT_ID)

_anonymizer = AnonymizerEngine()

_ENTITIES = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "JP_PHONE_NUMBER",
    "RAKUTEN_MERCHANT_ID",
    "CREDIT_CARD",
    "IBAN_CODE",
    "IP_ADDRESS",
    "PERSON",
]


class PIIProtector:
    def mask(self, text: str, language: str = "ja") -> str:
        """Replace PII with placeholder tags. Returns masked text."""
        lang_code = "ja" if language == "ja" else "en"
        try:
            results = _analyzer.analyze(
                text=text,
                entities=_ENTITIES,
                language=lang_code if lang_code == "en" else "en",  # Presidio uses EN model for JP too
            )
            if not results:
                return text
            anonymized = _anonymizer.anonymize(text=text, analyzer_results=results)
            return anonymized.text
        except Exception as exc:
            log.warning("PII masking error: %s", exc)
            return text  # fail-open: return original rather than crash

    def contains_pii(self, text: str) -> bool:
        """Quick check — returns True if any PII detected."""
        results = _analyzer.analyze(text=text, entities=_ENTITIES, language="en")
        return len(results) > 0
