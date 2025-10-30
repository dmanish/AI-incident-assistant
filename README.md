# 🧠 AI Incident Assistant

An intelligent assistant that automates **incident response reasoning**, **log analysis**, and **policy lookup** — combining **RAG**, **agentic tool use**, and **data-loss prevention**.

> 📖 **New here?** See [QUICKSTART.md](QUICKSTART.md) for the fastest way to get started!

---

## 🚀 Quick Start - One Command Setup

This project is designed to run with **ONE COMMAND** in both environments:

### ⚡ GitHub Codespaces
```bash
./start-codespaces.sh
```

### 🐳 Docker (Local Laptop)
```bash
./start-docker.sh
```

Both scripts will:
- ✅ Create `.env` from `.env.example` if needed
- ✅ Install/build dependencies automatically
- ✅ Bootstrap sample data
- ✅ Start backend API (port 8080)
- ✅ Start React UI (port 3000)

---

## 📋 Detailed Setup Instructions

### ✅ Option 1 — Run Directly in GitHub Codespaces

**One Command:**
```bash
./start-codespaces.sh
```

This script will:
1. Create `.env` from template (if needed)
2. Install Python and Node dependencies
3. Bootstrap and ingest sample security data
4. Start the backend API on port 8080
5. Start the React UI on port 3000

#### URLs (within Codespaces)

- **API Backend** → `https://<your-codespace-id>-8080.app.github.dev/healthz`
- **React UI** → `https://<your-codespace-id>-3000.app.github.dev/`

💡 *If the backend port is marked "Private", make it "Public" in the Codespaces Ports tab to allow the UI to access it.*

#### Manual Setup (if preferred)

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Install Node dependencies
cd frontend && npm install && cd ..

# 3. Bootstrap and ingest sample data
python scripts/bootstrap.py

# 4. Start the backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080

# 5. In a new terminal, start the React UI
cd frontend
VITE_BACKEND_URL=http://localhost:8080 npm run dev
```

---

### 🐳 Option 2 — Run with Docker Compose (Local or Codespaces)

**One Command:**
```bash
./start-docker.sh
```

This script:
- Auto-detects whether you're in **Codespaces** or running **locally**
- Sets the correct backend URL for the frontend
- Builds and starts both backend and frontend containers

This will:
- Build images using the Dockerfile in `docker/`
- Run the backend (`ai-incident-api`) on port **8080**
- Run the frontend (`ai-incident-web`) on port **3000**
- Run bootstrap + ingestion automatically inside the API container

#### Access the apps

**Local Docker:**
- **Backend API health** → [http://localhost:8080/healthz](http://localhost:8080/healthz)
- **React UI** → [http://localhost:3000](http://localhost:3000)

**Codespaces:**
- **Backend API** → `https://<your-codespace-id>-8080.app.github.dev/healthz`
- **React UI** → `https://<your-codespace-id>-3000.app.github.dev/`

💡 *In Codespaces, make sure port 8080 is set to "Public" in the Ports tab.*

#### To stop and clean up:
```bash
docker compose -f docker/docker-compose.yml down
```

---

## ⚙️ Environment Variables (`.env.local.sh` Example)

```bash
# FastAPI & JWT
export JWT_SECRET="devsecret"
export JWT_EXP_SECS=3600

# Database / Storage
export CHROMA_DB_DIR="/app/data/chroma"
export AUDIT_DIR="/app/data/logs"
export DUCK_DB_PATH="/app/data/logs/security.duckdb"

# LLM Configuration
# Options:
#   - empty → use local CPU embeddings
#   - OpenAI key → use text-embedding-3-small
export OPENAI_API_KEY="sk-..."

# Model: gpt-4o-mini or gpt-4-turbo-preview
export OPENAI_MODEL="gpt-4o-mini"

# URL for frontend
export BACKEND_URL="http://localhost:8080"
```

Make sure to **`source .env.local.sh`** before starting the app.

---

## 🧩 Features

| Capability | Description |
|-------------|-------------|
| 🔐 **RBAC** | Users (Security, Engineering, Sales) have tool- and document-level access control. |
| 📚 **Simple RAG** | Uses Chroma for vector search over seeded playbooks, policies, and KBs. |
| 🔍 **Agentic Tool Use** | Agent autonomously chooses between RAG and log query tool. |
| 🧾 **Audit Logging** | Every user, query, and LLM call logged in `data/logs/audit.log`. |
| 🧱 **DLP / Data Masking** | Regex + entropy + keyword-based masking before returning outputs. |
| ⚙️ **Dockerized Setup** | Complete reproducible environment with FastAPI + UI containers. |

---

## 🧠 Developer Guide

### 🧩 Architecture Overview

| Component | Tech | Description |
|------------|------|-------------|
| **Backend** | FastAPI (Python 3.11) | Main API, RAG retrieval, LLM orchestration, and tools |
| **Vector Store** | Chroma | Embedding + semantic search over security policies and playbooks |
| **LLM** | OpenAI API or Local | Generates summaries, reasoning, and answers |
| **Frontend** | React + TypeScript + Vite | Provides chat UI, visualization of retrieved docs & tool calls |
| **Database** | DuckDB | Used for log query simulation |
| **DLP Layer** | Regex + entropy + keyword list | Masks sensitive data before responses |

---

### 🧠 Extending the Agent

To add a **new tool** (e.g., threat feed lookup or ticket creation):

1. Create a new Python module in `app/tools/` (e.g., `app/tools/threatfeed.py`).
2. Define a simple function signature like:
   ```python
   def query_threat_feed(ioc: str) -> dict:
       # fetch data
       return {...}
   ```
3. Register it inside `/app/main.py` where `tool_calls` are processed.
4. Update `POLICY.yaml` to restrict access to specific roles.

---

### 🧩 Adding More RAG Data

To index new internal docs (playbooks, policies, etc.):  
1. Place Markdown files under `/data/docs/`  
2. Run:
   ```bash
   python scripts/ingest.py
   ```
   or (for protected mode):
   ```bash
   python scripts/ingest_guard.py
   ```

---

### 🧠 Debugging Tips

| Symptom | Check |
|----------|--------|
| LLM replies always say "Here's a concise answer based on what I can see locally" | Missing or invalid `OPENAI_API_KEY`. |
| `/chat` fails with `"Log query failed"` | Ensure `data/logs/auth/*.csv` exist (run `scripts/bootstrap.py`). |
| Docker container exits | Likely missing `.env` or misreferenced paths in `docker-compose.yml`. |
| UI shows "failed to fetch" on login | **Codespaces**: Ensure port 8080 is "Public" in Ports tab. **Docker**: Stop and restart with `./start-docker.sh` to auto-configure backend URL. **Browser**: Hard refresh (Ctrl+Shift+R) to clear cache. |

---

### 🧰 Testing the Agent

| Use Case | Example Command | Expected Outcome | Code Flow |
|-----------|-----------------|------------------|------------|
| Retrieve policy info | “How to handle phishing email?” | RAG retrieves from playbook | `/agent/chat → RAG → LLM summarize` |
| Log query | “Show me today’s failed logins for jdoe” | Queries DuckDB logs | `/agent/chat → log_query → LLM format` |
| Mixed reasoning | “Any recent CVE for TLS?” | RAG or web search triggered | `/agent/chat → tool_router → LLM decide` |
| DLP test | “What’s my token ABCDEFGHIJKLMNOPQRSTUVWXYZ123456?” | Masked output `[REDACTED]` | Post-LLM DLP filter |

---

### 📊 Audit Logs

All significant events are stored in `data/logs/audit.log` as JSON lines.  
You can inspect them via:

```bash
tail -f data/logs/audit.log | jq
```

---

### 🧩 Future Stretch Goals

| Goal | Description |
|------|--------------|
| 🧠 Full LangChain Agent | Replace rule-based routing with true LLM reasoning for tool selection |
| 🌐 Web Search Integration | Add external enrichment (CVE, IP, threat intel APIs) |
| 🔒 Contextual DLP | Role-based masking & redaction |
| 📈 Observability | Add Prometheus metrics & OpenTelemetry traces |

---

### 👩‍💻 Contributors
- **Manish Dahiya** — Lead developer  

---

### 🧩 License
MIT License © 2025 Manish Dahiya

