"""Unit tests for semantic cache similarity logic."""
import pytest
from backend.memory.semantic_cache import _cosine


def test_identical_vectors_score_one() -> None:
    v = [1.0, 0.5, 0.25]
    assert abs(_cosine(v, v) - 1.0) < 1e-6


def test_orthogonal_vectors_score_zero() -> None:
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert abs(_cosine(a, b)) < 1e-6


def test_zero_vector_returns_zero() -> None:
    a = [0.0, 0.0, 0.0]
    b = [1.0, 2.0, 3.0]
    assert _cosine(a, b) == 0.0
