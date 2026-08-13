"""Store specialist agent — delegates to base make_specialist_agent factory."""
from backend.agents.specialists.base import make_specialist_agent

store_agent = make_specialist_agent("store")

__all__ = ["store_agent"]
