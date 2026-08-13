"""Embedding utilities — thin wrapper around azure_openai.embed_text."""
from backend.llm.azure_openai import embed_text, embed_batch

__all__ = ["embed_text", "embed_batch"]
