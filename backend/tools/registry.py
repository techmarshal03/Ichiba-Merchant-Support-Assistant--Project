"""
Tool registry — maps domain + merchant tier to available LangChain tools.
"""
from __future__ import annotations

from backend.tools.knowledge_search import knowledge_search_tool
from backend.tools.order_lookup import order_lookup_tool
from backend.tools.settlement_query import settlement_query_tool
from backend.tools.campaign_eligibility import campaign_eligibility_tool
from backend.tools.rms_api_docs import rms_api_docs_tool

# Tier → unlocked tools (additive)
TOOL_PERMISSIONS: dict[str, list[str]] = {
    "standard": ["knowledge_search", "rms_api_docs"],
    "gold":     ["knowledge_search", "rms_api_docs", "order_lookup", "campaign_eligibility"],
    "platinum": ["knowledge_search", "rms_api_docs", "order_lookup", "campaign_eligibility", "settlement_query"],
}

_ALL_TOOLS = {
    "knowledge_search":     knowledge_search_tool,
    "order_lookup":         order_lookup_tool,
    "settlement_query":     settlement_query_tool,
    "campaign_eligibility": campaign_eligibility_tool,
    "rms_api_docs":         rms_api_docs_tool,
}


def get_domain_tools(domain: str, tier: str = "standard") -> list:
    """Return LangChain tool instances allowed for this merchant's tier."""
    allowed = set(TOOL_PERMISSIONS.get(tier, TOOL_PERMISSIONS["standard"]))
    return [tool for name, tool in _ALL_TOOLS.items() if name in allowed]
