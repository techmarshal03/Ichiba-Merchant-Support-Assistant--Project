"""
Language-aware document chunker.
JP: 512-char chunks, overlap 64, Japanese sentence separators.
EN: 800-token chunks, overlap 100.
"""
from __future__ import annotations

from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class ChunkConfig:
    chunk_size: int
    chunk_overlap: int
    separators: list[str]
    length_function: str  # "char" | "token"


JP_CONFIG = ChunkConfig(
    chunk_size=512,
    chunk_overlap=64,
    separators=["。\n", "。", "\n\n", "\n", "、", ""],
    length_function="char",
)

EN_CONFIG = ChunkConfig(
    chunk_size=800,
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", " ", ""],
    length_function="token",
)


def chunk_document(text: str, language: str = "ja") -> list[str]:
    """Split document into retrieval-optimised chunks."""
    cfg = JP_CONFIG if language == "ja" else EN_CONFIG

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
        separators=cfg.separators,
        length_function=len if cfg.length_function == "char" else _token_len,
        is_separator_regex=False,
    )
    return splitter.split_text(text)


def _token_len(text: str) -> int:
    """Approximate token count (4 chars per token for EN)."""
    return len(text) // 4
