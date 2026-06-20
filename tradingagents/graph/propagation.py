# TradingAgents/graph/propagation.py

from typing import Dict, Any, cast
from langchain_core.messages import HumanMessage
from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)


class Propagator:
    """Handles state initialization and propagation through the graph."""

    def __init__(self, max_recur_limit=200):
        """Initialize with configuration parameters."""
        self.max_recur_limit = max_recur_limit

    def create_initial_state(
        self, asset_name: str, trade_date: str,
        investment_preferences: str = "",
        external_reports: list[str] = []
    ) -> AgentState:
        """Create the initial state for the agent graph."""
        invest_state = cast(InvestDebateState, {
            "bull_history": "",
            "bear_history": "",
            "history": "",
            "current_response": "",
            "judge_decision": "",
            "count": 0,
        })
        risk_state = cast(RiskDebateState, {
            "risky_history": "",
            "safe_history": "",
            "neutral_history": "",
            "history": "",
            "latest_speaker": "",
            "current_risky_response": "",
            "current_safe_response": "",
            "current_neutral_response": "",
            "judge_decision": "",
            "count": 0,
        })
        return cast(AgentState, {
            "messages": [HumanMessage(content=asset_name)],
            "asset_of_interest": asset_name,
            "trade_date": str(trade_date),
            "investment_preferences": str(investment_preferences),
            "investment_debate_state": invest_state,
            "risk_debate_state": risk_state,
            "market_report": "",
            "fundamentals_report": "",
            "sentiment_report": "",
            "news_report": "",
            "external_reports": external_reports,
        })

    def get_graph_args(self) -> Dict[str, Any]:
        """Get arguments for the graph invocation."""
        return {
            "stream_mode": "values",
            "config": {"recursion_limit": self.max_recur_limit},
        }
