#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# CryptoTradingAgents Docker Entrypoint
# ---------------------------------------------------------------------------

STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"
STREAMLIT_SERVER_HEADLESS="${STREAMLIT_SERVER_HEADLESS:-true}"
STREAMLIT_SERVER_ENABLE_CORS="${STREAMLIT_SERVER_ENABLE_CORS:-false}"
STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION="${STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION:-true}"
STREAMLIT_BROWSER_GATHER_USAGE_STATS="${STREAMLIT_BROWSER_GATHER_USAGE_STATS:-false}"

echo "============================================"
echo " CryptoTradingAgents - Starting Streamlit"
echo " Port:     ${STREAMLIT_PORT}"
echo " Headless: ${STREAMLIT_SERVER_HEADLESS}"
echo "============================================"

exec streamlit run app.py \
    --server.port="${STREAMLIT_PORT}" \
    --server.headless="${STREAMLIT_SERVER_HEADLESS}" \
    --server.enableCORS="${STREAMLIT_SERVER_ENABLE_CORS}" \
    --server.enableXsrfProtection="${STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION}" \
    --browser.gatherUsageStats="${STREAMLIT_BROWSER_GATHER_USAGE_STATS}" \
    "$@"
