# 🧠 AI Incident Assistant

This project is a **security incident assistant** that combines **LLM-based reasoning** with **log analysis** and **policy retrieval (RAG)**.  
It helps security or engineering users answer questions like:
> “Show me today’s failed login attempts for user `jdoe`”  
> “What’s the escalation path for a production outage caused by a security breach?”

---

## 🚀 How to Run

This project supports **two modes**:
- **Option 1 – Run directly in GitHub Codespaces** (best for development/demo)
- **Option 2 – Run locally with Docker Compose** (best for reproducible local or production-style setups)

---

### ✅ Option 1 — Run Directly in GitHub Codespaces

This is the simplest and fastest setup.  
All dependencies are automatically installed and data is bootstrapped on startup.

#### Steps

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Bootstrap and ingest sample data
python scripts/bootstrap.py

# 3. Start the backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080

# 4. (Optional) Start the Streamlit UI in a new terminal
streamlit run frontend/streamlit_app.py
```

#### URLs (within Codespaces)

- **API Backend** → <https://<your-codespace-id>-8080.app.github.dev/healthz>  
- **Streamlit UI** → <https://<your-codespace-id>-8501.app.github.dev/>

💡 *If the backend port is marked “Private”, make it “Public” in the Codespaces Ports tab to allow Streamlit access.*

---

### 🐳 Option 2 — Run Locally with Docker Compose

This method mirrors how the assistant would run in production:  
isolated containers for **API** and **UI**, both talking over an internal Docker network.

#### Steps

```bash
# 1. Build and start everything
docker compose -f docker/docker-compose.yml up --build
```

This will:
- Build images using the Dockerfile in `docker/`
- Run the backend (`ai-incident-api`) on port **8080**
- Run the frontend (`ai-incident-ui`) on port **8501**
- Run bootstrap + ingestion automatically inside the API container

#### Access the apps

- **Backend API health** → [http://localhost:8080/healthz](http://localhost:8080/healthz)  
  → should return `ok`
- **Streamlit UI** → [http://localhost:8501](http://localhost:8501)

---

## 🧩 Container Management & Debugging

### Inspect running containers
```bash
docker ps
```

### Enter the API container shell
```bash
docker exec -it ai-incident-api /bin/bash
```

### Check logs
```bash
docker logs -f ai-incident-api
docker logs -f ai-incident-ui
```

### Restart only the API service
```bash
docker compose restart api
```

---

## ⚙️ Environment Configuration

All runtime configuration lives in `.env.local.sh` (for local Docker) or `.env` (for Codespaces).

Example `.env.local.sh`:

```bash
#!/usr/bin/env bash
# ===============================
# AI Incident Assistant Settings
# ===============================

# OpenAI API key (optional; fallback to CPU embeddings if missing)
export OPENAI_API_KEY="sk-..."

# JWT secret for authentication tokens
export JWT_SECRET="supersecret"

# Which embedding backend to use: openai or local
#   local  → all-MiniLM-L6-v2 (CPU)
#   openai → text-embedding-3-small
export EMBED_BACKEND="local"

# Backend & data directories
export CHROMA_DB_DIR="/app/data/chroma"
export DUCK_DB_PATH="/app/data/logs/security.duckdb"

# Audit log directory
export AUDIT_DIR="/app/data/logs"

# Streamlit backend URL (used by UI)
export BACKEND_URL="http://ai-incident-api:8080"

echo "✅ Environment variables loaded successfully."
```

Make it executable:
```bash
chmod +x .env.local.sh
```

---

## 💬 API Quick Test

Once running, verify the `/chat` route works:

```bash
# 1. Login to get a token
curl -s -X POST http://localhost:8080/login   -H "Content-Type: application/json"   -d '{"email":"alice@company","password":"pass1"}' | jq .

# 2. Use the token in chat
curl -s -X POST http://localhost:8080/chat   -H "Authorization: Bearer <paste_token_here>"   -H "Content-Type: application/json"   -d '{"message":"Show me today’s failed login attempts for username jdoe"}' | jq .
```

