"""Campaign eligibility checker (gold+ tier)."""
from __future__ import annotations

from langchain_core.tools import tool


@tool
async def campaign_eligibility_tool(campaign_name: str) -> str:
    """
    Check if the merchant's store is eligible for a specific campaign.
    Available for Gold and Platinum tier merchants.

    Args:
        campaign_name: Campaign name (e.g. 'Super Sale', 'Shopping Marathon')
    """
    return (
        f"Eligibility check for '{campaign_name}': "
        "Please verify current eligibility in RMS > Marketing > Campaign Management. "
        "Eligibility criteria include store rating, sales history, and compliance status."
    )
