import os
import re
import json
import yaml
import duckdb
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt

# --- Env & Paths ---
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")  # no-op if not present; env vars from Compose will dominate

CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", str(ROOT / "data" / "chroma"))
AUDIT_DIR = Path(os.getenv("AUDIT_DIR", str(ROOT / "data" / "logs")))
DUCK_DB_PATH = os.getenv("DUCK_DB_PATH", str(ROOT / "data" / "logs" / "security.duckdb"))
POLICY_PATH = ROOT / "data" / "policies" / "policies.yaml"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
JWT_SECRET = os.getenv("JWT_SECRET", "devsecret")
JWT_EXP_SECS = int(os.getenv("JWT_EXP_SECS", "3600"))

# --- App ---
app = FastAPI(title="AI Incident Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- Audit logger (rotates daily, keep 14 days) ---
AUDIT_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("audit")
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler(
    filename=str(AUDIT_DIR / "audit.log"),
    when="D", interval=1, backupCount=14, encoding="utf-8"
)
logger.addHandler(handler)

def audit(event: Dict[str, Any]):
    event = {**event, "ts": datetime.utcnow().isoformat(timespec="seconds")}
    logger.info(json.dumps(event, ensure_ascii=False))

# --- RBAC policy ---
if POLICY_PATH.exists():
    with open(POLICY_PATH, "r") as f:
        POLICY = yaml.safe_load(f) or {}
else:
    POLICY = {
        "roles": {
            "security": {"allow_tools": ["log_query"], "allow_docs": ["policy","playbook","kb"]},
            "engineering": {"allow_tools": ["log_query"], "allow_docs": ["policy","playbook","kb"]},
            "sales": {"allow_tools": [], "allow_docs": ["kb"]},
        }
    }

def role_allows_tool(role: str, tool: str) -> bool:
    return tool in set(POLICY.get("roles", {}).get(role, {}).get("allow_tools", []))

def role_allows_doc(role: str, doc_type: str) -> bool:
    return doc_type in set(POLICY.get("roles", {}).get(role, {}).get("allow_docs", []))

# --- Users (demo) ---
USERS = {
    "alice@company": {"password": "pass1", "role": "security"},
    "bob@company": {"password": "pass2", "role": "engineering"},
    "sam@company": {"password": "pass3", "role": "sales"},
}

# --- JWT helpers ---
def create_jwt(email: str, role: str) -> str:
    payload = {
        "sub": email, "role": role,
        "exp": datetime.utcnow() + timedelta(seconds=JWT_EXP_SECS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_jwt(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def require_user(auth_header: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization: Bearer <token>")
    token = auth_header.split(" ", 1)[1]
    user = decode_jwt(token)
    return user

# --- Prompt-injection heuristics ---
INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"override the system",
    r"execute the following",
    r"system prompt",
    r"open the (?:file|socket|port)",
]
def is_injection(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in INJECTION_PATTERNS)

# --- Chroma retrieval (vector RAG) ---
# You already ingest via scripts/bootstrap.py & scripts/ingest.py
import chromadb
from chromadb import PersistentClient
chroma_client = PersistentClient(path=CHROMA_DB_DIR)
collection = None
try:
    collection = chroma_client.get_collection("security_docs")
except Exception:
    # Not yet created (e.g., if OPENAI_API_KEY wasn't set during bootstrap)
    collection = None

def retrieve_chunks(query: str, role: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Vector-only retrieval; hybrid (BM25+vector) can be added later."""
    if collection is None:
        return []
    res = collection.query(query_texts=[query], n_results=20, include=["documents","metadatas","distances"])
    docs = []
    for i in range(len(res["ids"][0])):
        meta = res["metadatas"][0][i] or {}
        doc_type = meta.get("doc_type", "kb")
        # RBAC doc filter
        if not role_allows_doc(role, doc_type):
            continue
        docs.append({
            "text": res["documents"][0][i],
            "metadata": meta,
            "score": float(res["distances"][0][i]) if res.get("distances") else None
        })
    # Take top_k after RBAC filter
    return docs[:top_k]

# --- DuckDB log query tool ---
con = duckdb.connect(DUCK_DB_PATH)
# Create external table over CSVs if not exists (bootstrap also seeds one CSV)
con.execute("""
    CREATE TABLE IF NOT EXISTS auth_logs AS
    SELECT * FROM read_csv_auto('./data/logs/auth', union_by_name=true, filename=true) WHERE 1=0
""")

def query_failed_logins(date_iso: str, username: Optional[str] = None, limit: int = 200):
    sql = """
        SELECT * FROM read_csv_auto('./data/logs/auth/*.csv', union_by_name=true)
        WHERE date(timestamp) = ?
          AND lower(result) = 'failed'
        {}
        ORDER BY timestamp DESC
        LIMIT ?
    """
    user_clause = "AND lower(user) = lower(?)" if username else ""
    params = [date_iso] + ([username] if username else []) + [limit]
    df = con.execute(sql.format(user_clause), params).fetchdf()
    return df

# --- OpenAI (chat) ---
from openai import OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def llm_answer(prompt: str) -> str:
    if not openai_client:
        # Safe fallback for dev without an API key
        return "LLM is not configured (missing OPENAI_API_KEY). Here's your prompt:\n\n" + prompt[:1200]
    resp = openai_client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system",
             "content": "You are a security assistant. Use provided context verbatim where appropriate. Be concise and include safe next steps."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=600,
    )
    return resp.choices[0].message.content

# --- Schemas ---
class LoginRequest(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    message: str
    convo_id: Optional[str] = None

# --- Routes ---
@app.get("/", response_class=PlainTextResponse)
def home():
    return "AI Incident Assistant (FastAPI) is running."

@app.get("/healthz", response_class=PlainTextResponse)
def healthz():
    return "ok"

@app.post("/login")
def login(req: LoginRequest):
    user = USERS.get(req.email)
    if not user or user["password"] != req.password:
        audit({"action": "login_failed", "email": req.email})
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_jwt(req.email, user["role"])
    audit({"action": "login_success", "email": req.email, "role": user["role"]})
    return {"token": token, "role": user["role"], "email": req.email}

@app.post("/chat")
def chat(req: ChatRequest, user=Depends(require_user)):
    role = user.get("role")
    # Prompt-injection guard
    if is_injection(req.message):
        audit({"action": "blocked_prompt_injection", "user": user["sub"], "role": role, "prompt": req.message})
        raise HTTPException(status_code=400, detail="Potential prompt injection detected and blocked.")

    # Agentic decision: call log tool if intent suggests
    tool_section = ""
    tool_calls = []
    msg_low = req.message.lower()
    if any(k in msg_low for k in ["failed login", "failed logins", "show logs", "login attempts"]):
        if not role_allows_tool(role, "log_query"):
            audit({"action": "unauthorized_tool_access", "user": user["sub"], "role": role, "tool": "log_query"})
            raise HTTPException(status_code=403, detail="Your role is not authorized to query logs.")
        # naive date parse: default to today UTC
        day = datetime.utcnow().date().isoformat()
        # optional username parse
        m = re.search(r"username\s+([a-z0-9_.-]+)", msg_low)
        username = m.group(1) if m else None
        try:
            df = query_failed_logins(day, username=username)
            sample = df.head(5).to_dict(orient="records")
            tool_section = f"\n---\nTool: log_query\nDate: {day}\nUsername: {username}\nFound: {len(df)} rows\nSample: {json.dumps(sample)[:1000]}"
            tool_calls.append({"tool": "log_query", "date": day, "username": username, "result_count": int(len(df))})
            audit({"action":"tool_call","user":user["sub"],"role":role,"tool":"log_query","filters":{"date":day,"username":username},"result_count":int(len(df))})
        except Exception as e:
            audit({"action":"tool_error","user":user["sub"],"role":role,"tool":"log_query","error":str(e)})
            raise HTTPException(status_code=500, detail="Log query failed")

    # Retrieval (RAG)
    retrieved = retrieve_chunks(req.message, role=role, top_k=5)
    rag_context = ""
    for r in retrieved:
        src = r["metadata"].get("source_path", "unknown")
        rag_context += f"\n---\nSource: {src}\n{r['text'][:1000]}"

    # Build final prompt for LLM
    final_prompt = f"{req.message}\n\nContext:{rag_context}{tool_section}"
    audit({"action":"llm_invoke","user":user["sub"],"role":role,"prompt_excerpt":final_prompt[:400]})
    try:
        answer = llm_answer(final_prompt)
    except Exception as e:
        audit({"action":"llm_error","user":user["sub"],"role":role,"error":str(e)})
        raise HTTPException(status_code=500, detail="LLM call failed")

    # (Optional) simple DLP mask for long tokens that look like secrets
    answer = re.sub(r"[A-Za-z0-9_\-]{24,}", "[REDACTED]", answer)

    audit({"action":"llm_result","user":user["sub"],"role":role,"result_excerpt":answer[:400]})
    return {"reply": answer, "retrieved": retrieved, "tool_calls": tool_calls}
