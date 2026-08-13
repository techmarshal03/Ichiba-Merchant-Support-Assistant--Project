"""Order specialist agent — delegates to base make_specialist_agent factory."""
from backend.agents.specialists.base import make_specialist_agent

order_agent = make_specialist_agent("order")

__all__ = ["order_agent"]
