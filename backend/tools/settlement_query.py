"""Settlement query tool — fetches payment summary (platinum tier only)."""
from __future__ import annotations

from langchain_core.tools import tool


@tool
async def settlement_query_tool(year_month: str) -> str:
    """
    Query settlement summary for a given month (YYYY-MM format).
    Available for Platinum tier merchants only.

    Args:
        year_month: Settlement period in YYYY-MM format (e.g. 2024-08)
    """
    return (
        f"Settlement data for {year_month}: Please download the full settlement report "
        "from RMS > Sales & Income > Settlement Report for detailed breakdowns."
    )
