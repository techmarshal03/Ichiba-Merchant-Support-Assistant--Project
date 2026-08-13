"""
Merchant authentication middleware using Azure API Management JWT validation.
Extracts and validates the merchant session from the Authorization header.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from backend.config import settings
from backend.memory.merchant_profile import MerchantProfile, get_merchant_profile

log = logging.getLogger(__name__)

security = HTTPBearer()


class MerchantSession(BaseModel):
    merchant_id: str
    session_id: str
    tier: str = "standard"
    preferred_language: str = "ja"
    store_name: Optional[str] = None


async def authenticate_merchant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> MerchantSession:
    """
    Validate JWT from Azure APIM and load merchant profile.
    Raises 401 on invalid token, 403 if merchant is inactive.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        log.warning("JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    merchant_id: str | None = payload.get("sub")
    session_id: str | None = payload.get("sid")

    if not merchant_id or not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required claims",
        )

    profile: MerchantProfile | None = await get_merchant_profile(merchant_id)
    if profile and not profile.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Merchant account is inactive",
        )

    return MerchantSession(
        merchant_id=merchant_id,
        session_id=session_id,
        tier=profile.tier if profile else "standard",
        preferred_language=profile.preferred_language if profile else "ja",
        store_name=profile.store_name if profile else None,
    )
