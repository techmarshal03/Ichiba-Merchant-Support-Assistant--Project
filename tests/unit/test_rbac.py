"""Unit tests for RBAC tool permissions."""
import pytest
from backend.security.rbac import get_domain_tools, TOOL_PERMISSIONS


def test_standard_tier_has_minimal_tools() -> None:
    tools = get_domain_tools("store", tier="standard")
    tool_names = {t.name for t in tools}
    assert "knowledge_search" in tool_names
    assert "settlement_query" not in tool_names


def test_platinum_tier_has_all_tools() -> None:
    tools = get_domain_tools("store", tier="platinum")
    tool_names = {t.name for t in tools}
    assert "settlement_query" in tool_names
    assert "order_lookup" in tool_names
    assert "campaign_eligibility" in tool_names


def test_gold_tier_intermediate_permissions() -> None:
    tools = get_domain_tools("order", tier="gold")
    tool_names = {t.name for t in tools}
    assert "order_lookup" in tool_names
    assert "settlement_query" not in tool_names


def test_invalid_tier_defaults_to_standard() -> None:
    tools = get_domain_tools("store", tier="unknown_tier")
    assert tools is not None
    assert len(tools) > 0
