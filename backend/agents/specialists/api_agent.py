"""Api specialist agent — delegates to base make_specialist_agent factory."""
from backend.agents.specialists.base import make_specialist_agent

api_agent = make_specialist_agent("api")

__all__ = ["api_agent"]
