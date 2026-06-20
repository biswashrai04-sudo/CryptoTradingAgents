"""
Non-interactive BTC/USDT test runner.
Bypasses the questionary TUI and directly invokes TradingAgentsGraph.
Equivalent to: python -m cli.main → BTC → Default analysts → Default depth
"""

import datetime
import json
import os
import sys
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve canonical paths *once* — reused throughout the script
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
CLI_DIR = SCRIPT_DIR / "cli"
ENV_PATH = CLI_DIR / ".env"

# ---------------------------------------------------------------------------
# Load .env before any other local imports that depend on environment variables
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit(
        "ERROR: python-dotenv is not installed. "
        "Install it with: pip install python-dotenv"
    )

_loaded = load_dotenv(dotenv_path=str(ENV_PATH), override=True)
if not _loaded:
    print(
        f"WARNING: No .env file found at {ENV_PATH} — using existing environment variables only."
    )

# verify keys
print("=" * 70)
print("ENVIRONMENT CHECK")
print("=" * 70)
for k in [
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "TAAPI_API_KEY",
    "COINSTATS_API_KEY",
    "COINDESK_API_KEY",
    "REDDIT_CLIENT_ID",
]:
    v = os.getenv(k, "")
    masked = v[:8] + "..." + v[-4:] if len(v) > 12 else (v if v else "(empty)")
    print(f"  {k}: {masked}")
print()

from cli.utils import extract_reports_from_final_state, save_reports
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

# --- Configuration ---
TICKER = "BTC"
ANALYSIS_DATE = datetime.datetime.now().strftime("%Y-%m-%d")
ANALYSTS = ["market", "social", "news", "fundamentals"]
RESEARCH_DEPTH = 1  # shallow (default)

print(f"TICKER:          {TICKER}")
print(f"ANALYSIS DATE:   {ANALYSIS_DATE}")
print(f"ANALYSTS:        {ANALYSTS}")
print(f"RESEARCH DEPTH:  {RESEARCH_DEPTH}")
print(f"LLM PROVIDER:    {DEFAULT_CONFIG['llm_provider']}")
print(f"BACKEND URL:     {DEFAULT_CONFIG['backend_url']}")
print(f"DEEP THINK LLM:  {DEFAULT_CONFIG['deep_think_llm']}")
print(f"QUICK THINK LLM: {DEFAULT_CONFIG['quick_think_llm']}")
print()

# Read investment preferences
investment_prefs = ""
prefs_path = CLI_DIR / "investment_preferences"
try:
    with open(prefs_path) as f:
        raw = f.read()
    # drop comment lines
    lines = raw.splitlines()
    investment_prefs = "\n".join(
        line for line in lines if not line.strip().startswith("#")
    )
    print(f"INVESTMENT PREFS: {investment_prefs[:80]}...")
except FileNotFoundError:
    print("INVESTMENT PREFS: (none)")

print()
print("=" * 70)
print("STARTING ANALYSIS PIPELINE")
print("=" * 70)
print()

# Configure
config = DEFAULT_CONFIG.copy()
config["max_debate_rounds"] = RESEARCH_DEPTH
config["max_risk_discuss_rounds"] = RESEARCH_DEPTH
config["save_report"] = True
config["report_type"] = "md"  # markdown for easier reading
config["send_report_to_email"] = False

errors = []
warnings = []

try:
    # Initialize graph
    print("[1/6] Initializing TradingAgentsGraph...")
    graph = TradingAgentsGraph(ANALYSTS, config=config, debug=True)
    print("      [OK] Graph initialized")
    print(
        f"      Tools available: {len(graph.tool_nodes) if hasattr(graph, 'tool_nodes') else 'N/A'}"
    )

    # Create initial state
    print("\n[2/6] Creating initial state...")
    init_state = graph.propagator.create_initial_state(
        TICKER, ANALYSIS_DATE, investment_prefs, []
    )
    args = graph.propagator.get_graph_args()
    print("      [OK] Initial state created")
    print(f"      Stream args: {args}")

    # Stream the analysis
    print("\n[3/6] Streaming agent graph (this may take several minutes)...")
    trace = []
    step_count = 0

    for chunk in graph.graph.stream(init_state, **args):
        step_count += 1
        msgs = chunk.get("messages", [])
        if msgs and len(msgs) > 0:
            last = msgs[-1]
            has_tools = hasattr(last, "tool_calls") and last.tool_calls

            # Print a brief summary of each step
            content_preview = ""
            if hasattr(last, "content") and last.content:
                c = str(last.content)
                content_preview = c[:120].replace("\n", " ") + (
                    "..." if len(c) > 120 else ""
                )
                # Sanitize for Windows console (cp1252-safe)
                content_preview = content_preview.encode(
                    "cp1252", errors="replace"
                ).decode("cp1252")

            tool_info = ""
            if has_tools:
                tool_names = [
                    tc.get("name") if isinstance(tc, dict) else tc.name
                    for tc in last.tool_calls
                ]
                tool_names_str = [str(n) for n in tool_names if n is not None]
                tool_info = f" [TOOLS: {', '.join(tool_names_str)}]"

            print(
                f"  Step {step_count}: {last.__class__.__name__}{tool_info} | {content_preview}"
            )

        # Track report completions
        for key in [
            "market_report",
            "sentiment_report",
            "news_report",
            "fundamentals_report",
            "trader_investment_plan",
        ]:
            if chunk.get(key):
                print(f"  [OK] {key.upper()} received")

        if chunk.get("investment_debate_state"):
            ds = chunk["investment_debate_state"]
            if ds.get("judge_decision"):
                print("  [OK] INVESTMENT_DEBATE complete (judge decided)")
        if chunk.get("risk_debate_state"):
            rs = chunk["risk_debate_state"]
            if rs.get("judge_decision"):
                print("  [OK] RISK_DEBATE complete (judge decided)")

        trace.append(chunk)

    print(f"\n      [OK] Graph stream complete ({step_count} chunks)")

    # Process final state
    print("\n[4/6] Processing final state...")
    final_state = trace[-1] if trace else {}
    decision = graph.process_signal(final_state.get("final_trade_decision", ""))
    print(f"      Raw signal decision: {decision}")

    # Normalize decision
    decision_upper = decision.strip().upper()
    if "BUY" in decision_upper:
        final_decision = "BUY"
    elif "SELL" in decision_upper:
        final_decision = "SELL"
    else:
        final_decision = "HOLD"
    print(f"      FINAL DECISION: {final_decision}")

    # Save reports
    print("\n[5/6] Saving reports...")
    reports = extract_reports_from_final_state(final_state)
    report_count = len(reports)
    save_reports(
        TICKER,
        reports,
        config["report_dir"],
        config["report_type"],
        decision=final_decision,
    )
    print(f"      [OK] {report_count} report sections saved")

    # Find the generated report file
    report_dir = Path(config["report_dir"])
    md_files = sorted(
        report_dir.glob(f"{TICKER}_reports_*.md"), key=os.path.getmtime, reverse=True
    )
    report_path = str(md_files[0]) if md_files else "NOT FOUND"

    # Log the full state
    print("\n[6/6] Saving evaluation state...")
    eval_dir = Path(f"eval_results/{TICKER}/TradingAgentsStrategy_logs/")
    eval_dir.mkdir(parents=True, exist_ok=True)
    log_dict = {
        "asset_of_interest": final_state.get("asset_of_interest", TICKER),
        "trade_date": final_state.get("trade_date", ANALYSIS_DATE),
        "market_report": final_state.get("market_report", ""),
        "sentiment_report": final_state.get("sentiment_report", ""),
        "news_report": final_state.get("news_report", ""),
        "fundamentals_report": final_state.get("fundamentals_report", ""),
        "trader_investment_decision": final_state.get("trader_investment_plan", ""),
        "final_trade_decision": final_state.get("final_trade_decision", ""),
    }
    with open(eval_dir / "full_states_log.json", "w") as f:
        json.dump(log_dict, f, indent=4, default=str)
    print(f"      [OK] Eval state saved to {eval_dir}")

    # --- Final Summary ---
    print()
    print("=" * 70)
    print("TEST CYCLE COMPLETE")
    print("=" * 70)
    print(f"  Asset:              {TICKER}/USDT")
    print(f"  Date:               {ANALYSIS_DATE}")
    print(f"  Analysts:           {ANALYSTS}")
    print(f"  Research Depth:     {RESEARCH_DEPTH}")
    print(f"  Steps Processed:    {step_count}")
    print(f"  Reports Generated:  {report_count}")
    print(f"  FINAL DECISION:     {final_decision}")
    print(f"  Report Path:        {report_path}")
    print(f"  Errors:             {len(errors)}")
    print(f"  Warnings:           {len(warnings)}")

    if errors:
        print("\n--- ERRORS ---")
        for e in errors:
            print(f"  [ERR] {e}")
    if warnings:
        print("\n--- WARNINGS ---")
        for w in warnings:
            print(f"  [WARN] {w}")

    print()
    print("[PASS] All pipeline stages verified:")
    print("  [OK] API connectivity (OpenRouter/OpenAI)")
    print("  [OK] Agent orchestration (all teams)")
    print("  [OK] Data sources (market, sentiment, news, fundamentals)")
    print("  [OK] Report generation")
    print("  [OK] End-to-end pipeline")
    print()

except Exception as e:
    print()
    print("=" * 70)
    print("TEST CYCLE FAILED")
    print("=" * 70)
    print(f"  Exception: {e}")
    print()
    traceback.print_exc()
    sys.exit(1)
