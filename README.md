# 🧠 AI Incident Assistant

An intelligent assistant that automates **incident response reasoning**, **log analysis**, and **policy lookup** — combining **RAG**, **agentic tool use**, and **data-loss prevention**.

---

## 🚀 Quick Start

You can run this project in two ways:

### **Option 1 — Run in GitHub Codespaces (Recommended for Demo)**

This is the easiest and fastest setup.

#### Steps:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Seed local data (docs, logs, embeddings)
python scripts/bootstrap.py

# 3. Start the FastAPI backend
python app/main.py
```

Visit:  
👉 **http://127.0.0.1:8080** → API  
👉 **http://127.0.0.1:8501** → Streamlit UI

---

### **Option 2 — Run Locally with Docker (Production-Style)**

This setup simulates a real microservice deployment with separate containers for:
- Backend API (FastAPI)
- UI (Streamlit or React)
- Agent tools

#### Steps:

```bash
# 1. Build and run containers
docker compose -f docker/docker-compose.yml up --build

# 2. Check health
curl http://localhost:8080/healthz

# 3. Open in browser
http://localhost:8080  → Backend API
http://localhost:8501  → Streamlit UI
http://localhost:3000  → React Agent UI (if enabled)
```

#### To stop and clean up:
```bash
docker compose down -v
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
| **Frontend** | React / Streamlit | Provides chat UI, visualization of retrieved docs & tool calls |
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
| LLM replies always say “Here’s a concise answer based on what I can see locally” | Missing or invalid `OPENAI_API_KEY`. |
| `/chat` fails with `"Log query failed"` | Ensure `data/logs/auth/*.csv` exist (run `scripts/bootstrap.py`). |
| Docker container exits | Likely missing `.env` or misreferenced paths in `docker-compose.yml`. |
| UI shows “failed to fetch” | Verify `BACKEND_URL` matches the FastAPI service (`http://api:8080` in compose). |

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

