"""Payment specialist agent — delegates to base make_specialist_agent factory."""
from backend.agents.specialists.base import make_specialist_agent

payment_agent = make_specialist_agent("payment")

__all__ = ["payment_agent"]
