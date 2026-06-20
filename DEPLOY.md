# ============================================================================
# CryptoTradingAgents - DEPLOY.md
# Production & Cloud Deployment Guide
# ============================================================================

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Streamlit Community Cloud (Easy)](#streamlit-community-cloud-easy)
3. [Quick Start (Docker Compose)](#quick-start-docker-compose)
4. [Manual Deployment](#manual-deployment)
5. [Cloud Deployments (AWS/GCP/Azure)](#cloud-deployments-awsgcpazure)
6. [Environment Variables](#environment-variables)
7. [TLS / HTTPS Setup](#tls--https-setup)
8. [Monitoring & Logs](#monitoring--logs)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Requirement      | Version / Notes                                       |
| ---------------- | ----------------------------------------------------- |
| Docker           | 24+ (with BuildKit enabled)                           |
| Docker Compose   | v2+ (plugin or standalone)                            |
| LLM API Key      | At least one: OpenRouter, OpenAI, Anthropic, Google   |
| Data API Keys    | Optional: CoinStats, CoinDesk, Reddit, TAAPI, FinnHub |

---

## Streamlit Community Cloud (Easy)

Streamlit Community Cloud is the **simplest free option**. It auto-deploys from a GitHub repo.

### Why It Wasn't Working Before

| Problem | Root Cause | Fix Applied |
|---------|-----------|-------------|
| `ModuleNotFoundError: No module named 'pandas'` | `requirements.txt` was missing `streamlit` — Community Cloud ignores `pyproject.toml` | Added `streamlit` to [`requirements.txt`](requirements.txt) |
| No API keys after deploy | All modules use `os.getenv()`, but Community Cloud provides keys via `st.secrets` only | Added `st.secrets` → `os.environ` bridge in [`app.py`](app.py:20-28) |
| No config | No `.streamlit/config.toml` existed | Created [`.streamlit/config.toml`](.streamlit/config.toml) with dark theme |
| No secrets template | Users didn't know what keys to add to Cloud Secrets | Created [`.streamlit/secrets.toml.template`](.streamlit/secrets.toml.template) |

### Step-by-Step Setup

#### 1. Fork / push the repo to GitHub
```bash
git clone https://github.com/TauricResearch/CryptoTradingAgents.git
cd CryptoTradingAgents
# Push to your own GitHub account
```

#### 2. Go to Streamlit Community Cloud
Visit [https://share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.

#### 3. Deploy the app
- Click **"New app"**
- Select your repository, branch, and set **Main file path** to `app.py`
- Click **Deploy**

#### 4. Add API keys (CRITICAL)
Once deployed, go to your app's **Settings → Secrets** and paste:

```toml
# REQUIRED — at least one LLM provider key
OPENROUTER_API_KEY = "sk-or-v1-..."
# OPENAI_API_KEY = "sk-..."

# OPTIONAL — data provider keys (improves analysis quality)
# TAAPI_API_KEY = "..."
# COINSTATS_API_KEY = "..."
# COINDESK_API_KEY = "..."
# REDDIT_CLIENT_ID = "..."
# REDDIT_CLIENT_SECRET = "..."
# REDDIT_USERNAME = "..."
# REDDIT_PASSWORD = "..."
# REDDIT_USER_AGENT = "CryptoTradingAgents/1.0"
```

Then **reboot** the app from the menu (⋮ → Reboot).

#### 5. Verify
Open your app URL. You should see:
- ✅ Market Overview table (CoinGecko prices)
- ✅ Sidebar with configuration options
- ✅ "Run Analysis" button ready to use

### Community Cloud Limitations
- **Resource caps:** 1 GB RAM, 1 CPU — use "Shallow" research depth for best results
- **Sleep after inactivity:** Free tier apps sleep after periods of inactivity
- **No persistent disk:** Reports saved to `/app/tradingagents/reports` are ephemeral (lost on reboot)
- **Timeout:** Long analysis runs may hit the 600s request timeout — keep `max_debate_rounds` at 1

### How It Works (Technical)
[`app.py`](app.py:18-28) does three things at startup:
1. Tries local `.env` files first (`./cli/.env`, `.env`)
2. Reads `st.secrets` and injects all string secrets into `os.environ`
3. Local `.env` values take precedence over Cloud secrets (so local dev still works)

All downstream modules read `os.getenv("OPENROUTER_API_KEY")` etc. — they never need to know about `st.secrets`.

---

## Quick Start (Docker Compose)

### 1. Clone & configure

```bash
git clone https://github.com/TauricResearch/CryptoTradingAgents.git
cd CryptoTradingAgents

# Copy and edit environment
cp cli/.env.example cli/.env
# Fill in your API keys in cli/.env
```

### 2. Build and launch

```bash
# Build the image
docker compose build

# Start the full stack (Streamlit + nginx reverse proxy)
docker compose up -d

# Check logs
docker compose logs -f streamlit
```

The app is now available at:
- **Direct:** `http://localhost:8501`
- **Via nginx:** `http://localhost`

### 3. Single-service (minimal)

```bash
# Run just the Streamlit container without nginx
docker compose up -d streamlit
```

---

## Manual Deployment

### Option A: uv / pip (bare metal)

```bash
# Install uv
pip install uv

# Sync dependencies
uv sync

# Run
streamlit run app.py --server.headless true --server.port 8501
```

### Option B: Python venv

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

pip install -r requirements.txt

streamlit run app.py --server.headless true --server.port 8501
```

---

## Cloud Deployments (AWS/GCP/Azure)

### AWS ECS / Fargate

1. Push the Docker image to ECR:
   ```bash
   aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
   docker tag cryptotradingagents:latest <ecr-repo>:latest
   docker push <ecr-repo>:latest
   ```

2. Create an ECS task definition using the container image.
3. Expose port 8501 via an Application Load Balancer (ALB).
4. Store API keys in AWS Secrets Manager or SSM Parameter Store.
5. Set up CloudWatch for logs.

**Recommended ALB health check:**
- Path: `/_stcore/health`
- Protocol: HTTP
- Port: 8501
- Healthy threshold: 2
- Interval: 30s

### GCP Cloud Run

```bash
gcloud run deploy cryptotradingagents \
    --image gcr.io/<project>/cryptotradingagents:latest \
    --platform managed \
    --region us-central1 \
    --port 8501 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 600 \
    --set-env-vars="STREAMLIT_SERVER_HEADLESS=true" \
    --set-secrets="OPENROUTER_API_KEY=openrouter-key:latest"
```

### Azure Container Apps

```bash
az containerapp create \
    --name cryptotradingagents \
    --resource-group <rg> \
    --image <registry>/cryptotradingagents:latest \
    --target-port 8501 \
    --ingress external \
    --cpu 2 --memory 2Gi \
    --env-vars STREAMLIT_SERVER_HEADLESS=true
```

### Railway / Render / Fly.io

These platforms auto-detect Dockerfiles. Push this repo and set:
- **Port:** 8501
- **Build command:** auto-detected from Dockerfile
- **Start command:** auto-detected from entrypoint

---

## Environment Variables

| Variable                          | Required | Default               | Description                        |
| --------------------------------- | -------- | --------------------- | ---------------------------------- |
| `OPENROUTER_API_KEY`              | Yes*     | —                     | OpenRouter API key                 |
| `OPENAI_API_KEY`                  | Yes*     | —                     | OpenAI API key (*one provider)     |
| `ANTHROPIC_API_KEY`               | No       | —                     | Anthropic API key                  |
| `GOOGLE_API_KEY`                  | No       | —                     | Google GenAI API key               |
| `DASHSCOPE_API_KEY`               | No       | —                     | Alibaba Qwen API key               |
| `GITEE_API_KEY`                   | No       | —                     | Gitee AI API key                   |
| `TAAPI_API_KEY`                   | No       | —                     | Technical Analysis data            |
| `COINSTATS_API_KEY`               | No       | —                     | CoinStats news/sentiment           |
| `COINDESK_API_KEY`                | No       | —                     | CoinDesk news                      |
| `REDDIT_CLIENT_ID`                | No       | —                     | Reddit social sentiment            |
| `REDDIT_CLIENT_SECRET`            | No       | —                     | Reddit social sentiment            |
| `REDDIT_USERNAME`                 | No       | —                     | Reddit auth                        |
| `REDDIT_PASSWORD`                 | No       | —                     | Reddit auth                        |
| `REDDIT_USER_AGENT`               | No       | —                     | Reddit user agent                  |
| `STREAMLIT_PORT`                  | No       | `8501`                | Streamlit listen port              |
| `STREAMLIT_SERVER_HEADLESS`       | No       | `true`                | Run without opening browser        |
| `STREAMLIT_SERVER_ENABLE_CORS`    | No       | `false`               | Enable CORS (set true behind proxy)|
| `NGINX_PORT`                      | No       | `80`                  | Nginx public port                  |
| `REDIS_PORT`                      | No       | `6379`                | Redis port                         |

---

## TLS / HTTPS Setup

### Using nginx + Let's Encrypt

1. Uncomment the HTTPS redirect and port 443 in [`nginx.conf`](nginx.conf).
2. Add certbot/Let's Encrypt volumes to `docker-compose.yml`:

```yaml
nginx:
  volumes:
    - ./certbot/www:/var/www/certbot:ro
    - ./certbot/conf:/etc/letsencrypt:ro
```

3. Run certbot to obtain certificates:
   ```bash
   docker compose run --rm certbot certonly --webroot ...
   ```

### Using Cloud Load Balancer (AWS ALB / GCP LB)

- Terminate TLS at the load balancer
- Route port 443 → port 80/8501 backend
- Use ACM (AWS) or Google-managed certificates

---

## Monitoring & Logs

### Docker logs

```bash
# Stream logs for a specific service
docker compose logs -f streamlit

# Tail last 100 lines
docker compose logs --tail 100 streamlit
```

### Health endpoints

- **Streamlit:** `GET /_stcore/health` → returns `200 OK` when healthy
- **Nginx:** `GET /_stcore/health` → proxied to Streamlit

### Prometheus / Grafana (add-on)

To add metrics, mount a `prometheus.yml` and add a Prometheus + Grafana service profile:

```yaml
profiles:
  - monitoring
```

---

## Troubleshooting

| Symptom                              | Likely Cause                         | Solution                                   |
| ------------------------------------ | ------------------------------------ | ------------------------------------------ |
| `ModuleNotFoundError: No module`     | Missing dependency in venv           | Run `uv sync`; Community Cloud: ensure `streamlit` is in `requirements.txt` |
| `Connection refused` on port 8501    | Streamlit not started                | Check `docker compose logs streamlit`       |
| Community Cloud: API key not found   | Secrets not configured               | Add keys in Settings → Secrets, then reboot |
| WebSocket disconnects                | Proxy misconfiguration               | Ensure nginx passes `Upgrade` headers       |
| Analysis hangs                       | LLM API timeout or rate limit        | Reduce `max_debate_rounds`; check API quota |
| Out of memory                        | Container OOM                        | Increase `deploy.resources.limits.memory`   |
| `KeyError` on LLM provider           | Unsupported provider in config       | Valid providers: openrouter, openai, qwen, anthropic, google, ollama, gitee |

For more help, consult the [Streamlit deployment docs](https://docs.streamlit.io/deploy) or open an issue on the repository.
