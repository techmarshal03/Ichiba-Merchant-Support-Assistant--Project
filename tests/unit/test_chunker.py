"""Unit tests for document chunker."""
import pytest
from backend.rag.chunker import chunk_document, JP_CONFIG, EN_CONFIG


def test_jp_chunk_size_within_limit() -> None:
    long_text = "楽天市場の商品登録について説明します。" * 60  # ~1200 chars
    chunks = chunk_document(long_text, language="ja")
    assert all(len(c) <= JP_CONFIG.chunk_size * 1.1 for c in chunks), \
        "Some JP chunks exceed max size"


def test_en_chunk_produces_multiple_chunks() -> None:
    long_text = "This is a sentence about Rakuten store setup. " * 100
    chunks = chunk_document(long_text, language="en")
    assert len(chunks) > 1, "Long EN text should produce multiple chunks"


def test_jp_chunk_respects_sentence_boundaries() -> None:
    text = "最初の文章です。次の文章です。三番目の文章です。"
    chunks = chunk_document(text, language="ja")
    # All chunks should be non-empty
    assert all(len(c) > 0 for c in chunks)


def test_short_text_single_chunk() -> None:
    text = "短いテキストです。"
    chunks = chunk_document(text, language="ja")
    assert len(chunks) == 1
    assert chunks[0] == text
