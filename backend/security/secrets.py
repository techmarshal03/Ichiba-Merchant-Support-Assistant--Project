"""
Secrets are injected via Azure Key Vault CSI Driver as env vars.
This module provides a thin validation layer at startup.
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

_REQUIRED_SECRETS = [
    "POSTGRES_DSN",
    "REDIS_CONNECTION_STRING",
    "COHERE_API_KEY",
]


def validate_secrets() -> None:
    """Assert all required secrets are present in the environment."""
    missing = [k for k in _REQUIRED_SECRETS if not os.environ.get(k)]
    if missing:
        raise RuntimeError(
            f"Missing required secrets: {missing}. "
            "Ensure Key Vault CSI Driver is configured and pod has Workload Identity."
        )
    log.info("All required secrets validated ✓")
