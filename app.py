"""
CryptoTradingAgents - Streamlit Web UI
A browser-based dashboard for the headless trading agent framework.
"""

import datetime
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from cli.utils import extract_reports_from_final_state, save_reports
from tradingagents.dataflows.coingecko_utils import fetch_live_prices
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

# ---------------------------------------------------------------------------
# API Key Loading — supports local .env AND Streamlit Community Cloud secrets
# ---------------------------------------------------------------------------
# 1. Load local .env files (for development / Docker)
load_dotenv("./cli/.env", override=True)
load_dotenv(".env", override=True)

# 2. Streamlit Community Cloud: inject st.secrets into os.environ
#    Community Cloud provides secrets via st.secrets dict, NOT as env vars.
#    All dataflow modules use os.getenv(), so we bridge the gap here.
#    Local .env values take precedence (already set above, won't be overwritten).
if hasattr(st, "secrets"):
    for key, value in st.secrets.items():
        if isinstance(value, str) and value and not os.getenv(key):
            os.environ[key] = str(value)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Crypto Trading Agents",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar – Configuration
# ---------------------------------------------------------------------------
st.sidebar.markdown("# ⚙️ Configuration")

asset = st.sidebar.selectbox(
    "Asset",
    options=["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE"],
    index=0,
    help="Select the cryptocurrency to analyze.",
)

research_depth = st.sidebar.selectbox(
    "Research Depth",
    options=[
        ("Shallow (1 round)", 1),
        ("Medium (3 rounds)", 3),
        ("Deep (5 rounds)", 5),
    ],
    index=1,
    format_func=lambda x: x[0],
    help="Number of debate/discussion rounds for research and risk teams.",
)

analysis_date = st.sidebar.date_input(
    "Analysis Date",
    value=datetime.date.today(),
    max_value=datetime.date.today(),
    help="Date for the analysis (cannot be in the future).",
)

# Analyst selection
st.sidebar.markdown("### Analyst Team")

available_analysts = [
    "Market Analyst",
    "Social Media Analyst",
    "News Analyst",
    "Fundamentals Analyst",
]

ANALYST_MAP = {
    "Market Analyst": "market",
    "Social Media Analyst": "social",
    "News Analyst": "news",
    "Fundamentals Analyst": "fundamentals",
}

preferred_defaults = [
    "Market Analyst",
    "News Analyst",
]

safe_defaults = [a for a in preferred_defaults if a in available_analysts]

selected_analysts = st.sidebar.multiselect(
    "Select Analyst Team",
    options=available_analysts,
    default=safe_defaults,
)
if not selected_analysts:
    st.sidebar.warning("Please select at least one analyst.")
    st.stop()

analyst_values = [ANALYST_MAP[a] for a in selected_analysts]

# LLM provider
st.sidebar.markdown("### LLM Settings")
llm_provider = st.sidebar.selectbox(
    "LLM Provider",
    options=["openrouter", "openai", "qwen", "anthropic", "google", "ollama", "gitee"],
    index=0,
)

# Quick-think model
quick_think_defaults = {
    "openrouter": "meta-llama/llama-4-scout:free",
    "openai": "gpt-4o-mini",
    "qwen": "qwen-turbo-latest",
    "anthropic": "claude-3-5-haiku-latest",
    "google": "gemini-2.0-flash",
    "ollama": "llama3.2",
    "gitee": "DeepSeek-V3",
}
deep_think_defaults = {
    "openrouter": "deepseek/deepseek-chat-v3-0324:free",
    "openai": "gpt-4o",
    "qwen": "qwq-plus",
    "anthropic": "claude-sonnet-4-0",
    "google": "gemini-2.5-flash-preview-05-20",
    "ollama": "qwen3",
    "gitee": "DeepSeek-V3",
}

quick_think_llm = st.sidebar.text_input(
    "Quick-Think Model",
    value=quick_think_defaults.get(llm_provider, "gpt-4o-mini"),
    help="Fast model for simple tasks.",
)
deep_think_llm = st.sidebar.text_input(
    "Deep-Think Model",
    value=deep_think_defaults.get(llm_provider, "gpt-4o"),
    help="Powerful model for complex reasoning.",
)

# Investment preferences (optional)
st.sidebar.markdown("### Investment Preferences")
use_preferences = st.sidebar.checkbox("Use custom investment preferences", value=False)
investment_preferences = ""
if use_preferences:
    # Try loading saved preferences
    try:
        with open("./cli/investment_preferences") as f:
            saved = f.read()
    except FileNotFoundError:
        saved = ""
    investment_preferences = st.sidebar.text_area(
        "Preferences",
        value=saved,
        height=150,
        placeholder="e.g., Focus on long-term growth, avoid meme coins...",
        help="Describe your investment preferences, strategy, or constraints.",
    )

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("📈 Crypto Trading Agents")
st.markdown(
    "AI-powered multi-agent trading analysis framework. "
    "Configure your analysis in the sidebar and click **Run Analysis** to begin."
)

# ---------------------------------------------------------------------------
# Market Overview
# ---------------------------------------------------------------------------
st.markdown("## 📊 Market Overview")


@st.cache_data(ttl=60)
def get_live_prices():
    return fetch_live_prices()


try:
    prices = get_live_prices()
    market_data = {
        "Ticker": [p["ticker"] for p in prices],
        "Current Price": [
            f"${p['price']:,.2f}" if p["price"] >= 1 else f"${p['price']:.4f}"
            for p in prices
        ],
        "24h Change": [p["change_24h"] for p in prices],
    }
    market_df = pd.DataFrame(market_data)
except Exception:
    market_data = {
        "Info": [
            "Could not fetch live prices from CoinGecko. Check your internet connection."
        ]
    }
    market_df = pd.DataFrame(market_data)
st.table(market_df)

# Reports directory (matches default_config's report_dir relative path logic)
reports_dir = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "tradingagents")), "reports"
)

# ---------------------------------------------------------------------------
# Run Analysis
# ---------------------------------------------------------------------------
if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
    if not analyst_values:
        st.error("Please select at least one analyst type in the sidebar.")
        st.stop()

    # Build configuration
    config = DEFAULT_CONFIG.copy()
    config["max_debate_rounds"] = research_depth[1]
    config["max_risk_discuss_rounds"] = research_depth[1]
    config["quick_think_llm"] = quick_think_llm
    config["deep_think_llm"] = deep_think_llm
    config["llm_provider"] = llm_provider

    # Progress placeholder
    progress_container = st.container()
    report_container = st.container()

    with progress_container:
        st.markdown("### 📊 Analysis Progress")
        progress_bar = st.progress(0, text="Initializing...")

        # Agent status table
        status_cols = st.columns(4)
        status_placeholders = {}

        team_agents = {
            "Analyst Team": [
                "Market Analyst",
                "Social Media Analyst",
                "News Analyst",
                "Fundamentals Analyst",
            ],
            "Research Team": ["Bull Researcher", "Bear Researcher", "Research Manager"],
            "Trading Team": ["Trader"],
            "Risk Management": [
                "Risky Analyst",
                "Safe Analyst",
                "Neutral Analyst",
                "Portfolio Manager",
            ],
        }

        for col_idx, (team, agents) in enumerate(team_agents.items()):
            with status_cols[col_idx % 4]:
                st.markdown(f"**{team}**")
                for agent in agents:
                    status_placeholders[agent] = st.empty()
                    status_placeholders[agent].markdown(f"⏳ {agent}")

    with report_container:
        st.markdown("### 📝 Analysis Reports")
        report_tabs = st.tabs(
            [
                "Market",
                "Sentiment",
                "News",
                "Fundamentals",
                "Research Debate",
                "Trader Plan",
                "Risk Debate",
                "Final Decision",
            ]
        )
        report_placeholders = {
            name: tab.empty()
            for name, tab in zip(
                [
                    "Market",
                    "Sentiment",
                    "News",
                    "Fundamentals",
                    "Research Debate",
                    "Trader Plan",
                    "Risk Debate",
                    "Final Decision",
                ],
                report_tabs,
            )
        }

    try:
        # Initialize graph
        graph = TradingAgentsGraph(
            selected_analysts=analyst_values,
            config=config,
            debug=False,
        )

        date_str = analysis_date.strftime("%Y-%m-%d")

        init_agent_state = graph.propagator.create_initial_state(
            asset_name=asset,
            trade_date=date_str,
            investment_preferences=investment_preferences,
            external_reports=[],
        )
        args = graph.propagator.get_graph_args()

        # Helper: update agent status
        def set_status(agent: str, status: str):
            icon = {"pending": "⏳", "running": "🔄", "done": "✅"}.get(status, "⏳")
            status_placeholders[agent].markdown(f"{icon} {agent}")

        # Stream with progress
        trace = []
        # Define a rough progress mapping per chunk type
        progress_steps = {
            "market_report": 0.05,
            "sentiment_report": 0.15,
            "news_report": 0.25,
            "fundamentals_report": 0.35,
            "investment_debate_state": 0.55,
            "trader_investment_plan": 0.65,
            "risk_debate_state": 0.85,
            "final_trade_decision": 0.95,
        }
        current_progress = 0.05

        for chunk in graph.graph.stream(init_agent_state, **args):
            if len(chunk.get("messages", [])) > 0:
                trace.append(chunk)

            # Market report
            if chunk.get("market_report"):
                report_placeholders["Market"].markdown(chunk["market_report"])
                set_status("Market Analyst", "done")
                progress_bar.progress(0.10, text="Market analysis complete")

            # Sentiment report
            if chunk.get("sentiment_report"):
                report_placeholders["Sentiment"].markdown(chunk["sentiment_report"])
                set_status("Social Media Analyst", "done")
                progress_bar.progress(0.20, text="Sentiment analysis complete")

            # News report
            if chunk.get("news_report"):
                report_placeholders["News"].markdown(chunk["news_report"])
                set_status("News Analyst", "done")
                progress_bar.progress(0.30, text="News analysis complete")

            # Fundamentals report
            if chunk.get("fundamentals_report"):
                report_placeholders["Fundamentals"].markdown(
                    chunk["fundamentals_report"]
                )
                set_status("Fundamentals Analyst", "done")
                progress_bar.progress(0.40, text="Fundamentals analysis complete")

            # Investment debate state
            if chunk.get("investment_debate_state"):
                debate = chunk["investment_debate_state"]
                parts = []
                if debate.get("bull_history"):
                    parts.append(f"**🐂 Bull Researcher:**\n\n{debate['bull_history']}")
                    set_status("Bull Researcher", "done")
                if debate.get("bear_history"):
                    parts.append(f"**🐻 Bear Researcher:**\n\n{debate['bear_history']}")
                    set_status("Bear Researcher", "done")
                if debate.get("judge_decision"):
                    parts.append(
                        f"**⚖️ Research Manager Decision:**\n\n{debate['judge_decision']}"
                    )
                    set_status("Research Manager", "done")
                if parts:
                    report_placeholders["Research Debate"].markdown(
                        "\n\n---\n\n".join(parts)
                    )
                progress_bar.progress(0.55, text="Research debate in progress...")

            # Trader plan
            if chunk.get("trader_investment_plan"):
                report_placeholders["Trader Plan"].markdown(
                    chunk["trader_investment_plan"]
                )
                set_status("Trader", "done")
                progress_bar.progress(0.70, text="Trader plan ready")

            # Risk debate state
            if chunk.get("risk_debate_state"):
                risk = chunk["risk_debate_state"]
                risk_parts = []
                if risk.get("current_risky_response"):
                    risk_parts.append(
                        f"**🔥 Aggressive Analyst:**\n\n{risk['current_risky_response']}"
                    )
                if risk.get("risky_history"):
                    risk_parts.append(
                        f"**🔥 Aggressive History:**\n\n{risk['risky_history']}"
                    )
                    set_status("Risky Analyst", "done")
                if risk.get("current_safe_response"):
                    risk_parts.append(
                        f"**🛡️ Conservative Analyst:**\n\n{risk['current_safe_response']}"
                    )
                if risk.get("safe_history"):
                    risk_parts.append(
                        f"**🛡️ Conservative History:**\n\n{risk['safe_history']}"
                    )
                    set_status("Safe Analyst", "done")
                if risk.get("current_neutral_response"):
                    risk_parts.append(
                        f"**⚖️ Neutral Analyst:**\n\n{risk['current_neutral_response']}"
                    )
                if risk.get("neutral_history"):
                    risk_parts.append(
                        f"**⚖️ Neutral History:**\n\n{risk['neutral_history']}"
                    )
                    set_status("Neutral Analyst", "done")
                if risk.get("judge_decision"):
                    risk_parts.append(
                        f"**🏆 Portfolio Manager Decision:**\n\n{risk['judge_decision']}"
                    )
                    set_status("Portfolio Manager", "done")
                if risk_parts:
                    report_placeholders["Risk Debate"].markdown(
                        "\n\n---\n\n".join(risk_parts)
                    )
                progress_bar.progress(0.85, text="Risk analysis in progress...")

        # Final state and decision
        if trace:
            final_state = trace[-1]
            decision = graph.process_signal(final_state.get("final_trade_decision", ""))

            # Display final decision
            decision_color = {
                "buy": "🟢",
                "sell": "🔴",
                "hold": "🟡",
            }.get(decision.lower(), "⚪")
            report_placeholders["Final Decision"].markdown(
                f"## {decision_color} Final Decision: **{decision.upper()}**\n\n"
                f"{final_state.get('final_trade_decision', '')}"
            )

            # Save reports
            if config.get("save_report", True):
                reports = extract_reports_from_final_state(final_state)
                save_reports(
                    asset,
                    reports,
                    reports_dir,
                    config.get("report_type", "md"),
                    decision=decision,
                )

            progress_bar.progress(1.0, text="✅ Analysis complete!")
            st.success(
                f"Analysis for {asset} completed! Decision: **{decision.upper()}**"
            )

            # Mark all as done
            for agent_name in status_placeholders:
                set_status(agent_name, "done")

    except Exception as e:
        st.error(f"Analysis failed: {e}")
        progress_bar.progress(1.0, text=f"❌ Error: {e}")

# ---------------------------------------------------------------------------
# Saved Reports
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 📁 Saved Reports")

if os.path.isdir(reports_dir):
    report_files = sorted(
        [f for f in os.listdir(reports_dir) if f.endswith((".md", ".pdf"))],
        reverse=True,
    )
    if report_files:
        for rf in report_files[:20]:  # Show last 20
            file_path = os.path.join(reports_dir, rf)
            if rf.endswith(".md"):
                with st.expander(f"📄 {rf}"):
                    try:
                        with open(file_path, encoding="utf-8") as f:
                            st.markdown(f.read())
                    except Exception:
                        st.info(
                            f"Markdown file: {rf} ({os.path.getsize(file_path):,} bytes)"
                        )
            else:
                st.markdown(f"📕 **{rf}** (PDF – {os.path.getsize(file_path):,} bytes)")
    else:
        st.info("No saved reports yet. Run an analysis to generate reports.")
else:
    os.makedirs(reports_dir, exist_ok=True)
    st.info("No saved reports yet. Run an analysis to generate reports.")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: grey;'>"
    "© <a href='https://github.com/TauricResearch' style='color: grey;'>Tauric Research</a> "
    "| Crypto Trading Agents</div>",
    unsafe_allow_html=True,
)
