"""Policy specialist agent — delegates to base make_specialist_agent factory."""
from backend.agents.specialists.base import make_specialist_agent

policy_agent = make_specialist_agent("policy")

__all__ = ["policy_agent"]
