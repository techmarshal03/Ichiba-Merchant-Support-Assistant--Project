"""
Merchant profile lookup from Azure Cosmos DB.
Provides tier, language preference, and store metadata.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from azure.cosmos.aio import CosmosClient
from pydantic import BaseModel

from backend.config import settings

log = logging.getLogger(__name__)


class MerchantProfile(BaseModel):
    merchant_id: str
    store_name: str
    tier: str = "standard"          # standard | gold | platinum
    preferred_language: str = "ja"  # ja | en
    store_domain: str | None = None
    active: bool = True


@lru_cache(maxsize=1)
def _get_cosmos_client() -> CosmosClient:
    return CosmosClient(
        url=settings.cosmos_db_endpoint,
        credential=settings.cosmos_db_key,
    )


async def get_merchant_profile(merchant_id: str) -> MerchantProfile | None:
    """Fetch merchant profile from Cosmos DB. Returns None if not found."""
    client = _get_cosmos_client()
    db = client.get_database_client(settings.cosmos_db_name)
    container = db.get_container_client("merchants")

    try:
        item = await container.read_item(item=merchant_id, partition_key=merchant_id)
        return MerchantProfile(**item)
    except Exception:
        log.warning("Merchant profile not found: %s", merchant_id)
        return None
