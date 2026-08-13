"""Order lookup tool — fetches order status from RMS API (gold+ tier only)."""
from __future__ import annotations

from langchain_core.tools import tool


@tool
async def order_lookup_tool(order_number: str) -> str:
    """
    Look up the status of a Rakuten order by order number.
    Available for Gold and Platinum tier merchants only.

    Args:
        order_number: Rakuten order number (e.g. 123456-20240801-00001)
    """
    # In production: call RMS Order API
    # GET https://api.rms.rakuten.co.jp/es/1.0/order/getOrder?orderNumber={order_number}
    return (
        f"Order {order_number}: Status lookup requires live RMS API integration. "
        "Please check RMS > Order Management > Order List for real-time status."
    )
