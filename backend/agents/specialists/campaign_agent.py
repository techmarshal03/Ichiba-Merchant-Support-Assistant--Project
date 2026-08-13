"""Campaign specialist agent — delegates to base make_specialist_agent factory."""
from backend.agents.specialists.base import make_specialist_agent

campaign_agent = make_specialist_agent("campaign")

__all__ = ["campaign_agent"]
