"""Unit tests for language detection logic."""
import pytest
from backend.agents.supervisor import _detect_language_heuristic


@pytest.mark.parametrize("text,expected", [
    ("楽天市場の店舗設定について教えてください", "ja"),
    ("How do I set up my Rakuten store?", "en"),
    ("RMS APIのorder.getOrderエンドポイントについて", "mixed"),
    ("スーパーSALEのエントリー方法", "ja"),
    ("What is the settlement cycle for platinum merchants?", "en"),
    ("注文キャンセルのAPIはどう使いますか？cancelOrderを教えて", "mixed"),
])
def test_heuristic_detection(text: str, expected: str) -> None:
    result = _detect_language_heuristic(text)
    assert result == expected, f"Expected '{expected}' for: {text[:40]}"


def test_empty_string_defaults_to_ja() -> None:
    assert _detect_language_heuristic("") == "ja"


def test_numbers_only_defaults_to_ja() -> None:
    assert _detect_language_heuristic("12345678") == "ja"
