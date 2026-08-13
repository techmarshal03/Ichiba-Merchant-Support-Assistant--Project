"""
Specialist agent factory — one function generates all 6 domain agents.
Each agent: Hybrid RAG retrieval → ReAct loop with tier-gated tools → draft response.
"""
from __future__ import annotations
import logging
from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent
from backend.agents.state import IchibaAgentState
from backend.config import settings
from backend.rag.retriever import hybrid_rag_retrieve
from backend.security.rbac import get_domain_tools

logger = logging.getLogger(__name__)

DOMAIN_MODELS = {
    "store":    "gpt4o-ichiba-prod",
    "order":    "gpt4o-ichiba-prod",
    "payment":  "gpt4o-ichiba-prod",
    "campaign": "gpt4o-ichiba-prod",
    "api":      "gpt4o-ichiba-prod",
    "policy":   "gpt4o-ichiba-prod",
}

def _load_prompt(domain: str, language: str) -> str:
    import importlib.resources, pathlib
    lang = language if language in ("ja", "en") else "ja"
    path = pathlib.Path(__file__).parent.parent / "llm" / "prompts" / lang / f"{domain}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"You are a specialist Rakuten Ichiba support agent for {domain}. Answer only from provided context."

def make_specialist_agent(domain: str):
    """Factory: returns an async node function for the given domain."""

    async def specialist_agent_node(state: IchibaAgentState, config: dict) -> dict:
        # 1. Hybrid RAG retrieval
        tier = state.merchant_session.tier if state.merchant_session else "standard"
        chunks = await hybrid_rag_retrieve(
            query=state.messages[-1].content,
            domain=domain,
            language=state.detected_language,
            merchant_tier=tier,
            top_k=8,
        )
        context = "\n\n".join(
            f"[{c.section_heading}]\n{c.content}" for c in chunks
        )

        # 2. Build system prompt with grounding context
        system_prompt = _load_prompt(domain, state.detected_language).format(
            context=context,
            store_id=state.merchant_session.store_id if state.merchant_session else "—",
            tier=tier,
        )

        # 3. Tier-gated tools
        tools = get_domain_tools(domain, state.merchant_session)

        # 4. ReAct agent
        model = AzureChatOpenAI(
            azure_deployment=DOMAIN_MODELS[domain],
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            temperature=0.2,
            streaming=True,
        )
        agent = create_react_agent(model=model, tools=tools, state_modifier=system_prompt)

        result = await agent.ainvoke(
            {"messages": state.messages},
            config={**config, "recursion_limit": state.max_iterations},
        )

        tool_calls = [
            m.tool_calls[0]["name"]
            for m in result["messages"]
            if hasattr(m, "tool_calls") and m.tool_calls
        ]

        return {
            "draft_response":   result["messages"][-1].content,
            "retrieved_chunks": chunks,
            "citations":        [c.source_url for c in chunks if c.score > 0.5],
            "tool_calls_made":  tool_calls,
            "assigned_agent":   domain,
        }

    specialist_agent_node.__name__ = f"{domain}_agent_node"
    return specialist_agent_node
