"""
Role-Based Access Control — tool permissions by merchant tier.
"""
from __future__ import annotations
from backend.agents.state import MerchantSession

TOOL_PERMISSIONS: dict[str, list[str]] = {
    "standard": [
        "knowledge_search",
        "faq_lookup",
        "order_status_public",
    ],
    "gold": [
        "knowledge_search",
        "faq_lookup",
        "order_status_public",
        "settlement_summary_query",
        "campaign_eligibility_check",
    ],
    "platinum": [
        "knowledge_search",
        "faq_lookup",
        "order_status_public",
        "settlement_summary_query",
        "campaign_eligibility_check",
        "rms_api_docs_search",
        "inventory_sync_status",
        "priority_escalation_queue",
    ],
}

# Domain → available tools (all tiers combined — filtered by TOOL_PERMISSIONS)
DOMAIN_TOOL_REGISTRY: dict[str, list] = {
    "store":    [],   # populated by tools/registry.py at startup
    "order":    [],
    "payment":  [],
    "campaign": [],
    "api":      [],
    "policy":   [],
}

def get_domain_tools(domain: str, merchant_session: MerchantSession | None) -> list:
    tier = merchant_session.tier if merchant_session else "standard"
    allowed = set(TOOL_PERMISSIONS.get(tier, TOOL_PERMISSIONS["standard"]))
    all_tools = DOMAIN_TOOL_REGISTRY.get(domain, [])
    return [t for t in all_tools if t.name in allowed]
