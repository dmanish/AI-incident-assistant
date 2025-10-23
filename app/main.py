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
from typing import Optional
from fastapi import Header, HTTPException
from openai import OpenAI
_openai_client = None

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

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

#----Helper -------
def fallback_answer(user_msg: str, rag_context: str, tool_section: str) -> str:
    """Offline fallback used when OpenAI is unavailable. Summarizes from context/tool results."""
    # Very small heuristic for the demo:
    msg = user_msg.lower()
    if "phishing" in msg:
        return (
            "Here’s a safe, high-level phishing response:\n"
            "1) Isolate the affected device from the network.\n"
            "2) Notify the security team / manager.\n"
            "3) Preserve the email (headers, links) and analyze in a sandbox.\n"
            "4) Reset credentials and enforce MFA if not enabled.\n"
            "5) Report the domain/sender and update mail gateway rules.\n"
            "6) Review the incident and update training/policies.\n"
            + ("\n\nContext used:\n" + rag_context[:600] if rag_context else "")
        )
    if "failed login" in msg or "login attempts" in msg:
        # Try to extract a count from the tool section if available
        import re
        m = re.search(r"Found:\s+(\d+)\s+rows", tool_section or "")
        count = m.group(1) if m else "some"
        return (
            f"I checked the authentication logs and found {count} failed login attempts for the period/filters you asked.\n"
            "Recommended next steps:\n"
            "• Correlate by IP, user, and time to detect patterns.\n"
            "• GeoIP/ASN reputation check for offending IPs.\n"
            "• Lock or step-up auth (MFA) on impacted accounts.\n"
            "• Review recent password resets and notify the user(s).\n"
            "• Add rules for repeated failures and alerting."
        )
    # Generic fallback
    return (
        "Here’s a concise answer based on what I can see locally.\n"
        + (("\nContext used:\n" + rag_context[:600]) if rag_context else "")
        + (("\n\nTool results summary:\n" + tool_section[:400]) if tool_section else "")
    )

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

def require_user(authorization: Optional[str] = Header(None, alias="Authorization")) -> dict:
    # Expect: Authorization: Bearer <token>
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization: Bearer <token>")
    token = authorization.split(" ", 1)[1]
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
    """
    Tolerant retrieval:
    - If collection is missing or has no vectors/embedding, return [].
    - Any Chroma errors are caught and logged; we continue without RAG.
    """
    if collection is None:
        audit({"action": "retrieval_skip", "reason": "no_collection"})
        return []
    try:
        res = collection.query(
            query_texts=[query],
            n_results=20,
            include=["documents", "metadatas", "distances", "embeddings"],  # embeddings just in case
        )
    except Exception as e:
        audit({"action": "retrieval_error", "error": str(e)})
        return []

    if not res or not res.get("ids") or not res["ids"] or not res["ids"][0]:
        return []

    out: List[Dict[str, Any]] = []
    docs0 = res.get("documents", [[]])[0] or []
    metas0 = res.get("metadatas", [[]])[0] or []
    dists0 = (res.get("distances", [[]]) or [[]])[0] or []

    for i in range(min(len(docs0), len(metas0))):
        meta = metas0[i] or {}
        doc_type = meta.get("doc_type", "kb")
        if not role_allows_doc(role, doc_type):
            continue
        out.append({
            "text": docs0[i],
            "metadata": meta,
            "score": float(dists0[i]) if i < len(dists0) and dists0[i] is not None else None,
        })

    return out[:top_k]

# --- DuckDB log query tool ---
from pathlib import Path
con = duckdb.connect(DUCK_DB_PATH)

# Ensure directory exists so glob doesn't fail later
LOG_DIR = ROOT / "data" / "logs" / "auth"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Create an empty table so queries won't crash if no CSVs yet
con.execute("""
    CREATE TABLE IF NOT EXISTS auth_logs (
        timestamp TIMESTAMP,
        user      VARCHAR,
        action    VARCHAR,
        result    VARCHAR,
        ip        VARCHAR
    )
""")

def query_failed_logins(date_iso: str, username: Optional[str] = None, limit: int = 200):
    """
    File-backed DuckDB, short-lived connection. Robust by filtering timestamp as text prefix.
    """
    import pandas as pd
    log_dir = ROOT / "data" / "logs" / "auth"
    log_dir.mkdir(parents=True, exist_ok=True)
    files = list(log_dir.glob("*.csv"))
    if not files:
        return pd.DataFrame([])

    con = duckdb.connect(DUCK_DB_PATH, read_only=False)
    try:
        con.execute("PRAGMA threads=2;")
        con.execute("PRAGMA memory_limit='256MB';")

        user_clause = "AND lower(user) = lower(?)" if username else ""
        sql = f"""
            SELECT timestamp, user, action, result, ip
            FROM read_csv_auto('{(log_dir / "*.csv").as_posix()}', union_by_name=true)
            WHERE cast(timestamp as varchar) LIKE ?
              AND lower(result) = 'failed'
              {user_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """
        params = [f"{date_iso}%"] + ([username] if username else []) + [limit]
        df = con.execute(sql, params).fetchdf()
        return df
    finally:
        con.close()


# --- OpenAI (chat) ---
# --- OpenAI (chat) ---
from openai import OpenAI
_openai_client = None

def get_openai_client():
    global _openai_client
    if _openai_client is not None:
        return _openai_client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        _openai_client = OpenAI(api_key=api_key)
        return _openai_client
    except TypeError as e:
        # Most common cause: httpx version mismatch
        # Clear client so future calls can retry after you fix deps
        _openai_client = None
        raise RuntimeError(
            f"OpenAI client init failed ({e}). Try: "
            'pip install --upgrade "openai>=1.52.0" "httpx>=0.27.2,<0.28" "httpx-sse>=0.4.0"'
        )

def get_openai_client():
    global _openai_client
    if _openai_client is not None:
        return _openai_client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    _openai_client = OpenAI(api_key=api_key)
    return _openai_client

def llm_answer(user_msg: str, rag_context: str, tool_section: str) -> str:
    """Try OpenAI; on any error return an offline fallback."""
    client = get_openai_client()
    if not client:
        return fallback_answer(user_msg, rag_context, tool_section)
    try:
        prompt = f"{user_msg}\n\nContext:{rag_context}{tool_section}"
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system",
                 "content": "You are a security assistant. Prefer policy/playbook excerpts from context. Be concise and give actionable next steps."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=600,
        )
        return resp.choices[0].message.content
    except Exception as e:
        audit({"action":"llm_fallback", "reason": str(e)})
        return fallback_answer(user_msg, rag_context, tool_section)

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

    # ----- Prompt-injection guard -----
    if is_injection(req.message):
        audit({"action": "blocked_prompt_injection", "user": user["sub"], "role": role, "prompt": req.message})
        raise HTTPException(status_code=400, detail="Potential prompt injection detected and blocked.")

    # ----- Agentic tool: log_query (RBAC + robust) -----
    tool_section = ""
    tool_calls = []
    msg_low = req.message.lower()

    if any(k in msg_low for k in ["failed login", "failed logins", "show logs", "login attempts"]):
        if not role_allows_tool(role, "log_query"):
            audit({"action": "unauthorized_tool_access", "user": user["sub"], "role": role, "tool": "log_query"})
            raise HTTPException(status_code=403, detail="Your role is not authorized to query logs.")

        # default to today (UTC); naive username parse
        day = datetime.utcnow().date().isoformat()
        m = re.search(r"username\s+([a-z0-9_.-]+)", msg_low)
        username = m.group(1) if m else None

        # robust query function (uses TIMESTAMP cast first, then string prefix)
        try:
            df = query_failed_logins(day, username=username)
            sample = df.head(5).to_dict(orient="records")
            sample = df.head(5).to_dict(orient="records")
            tool_section = (
                f"\n---\nTool: log_query\nDate: {day}\nUsername: {username}\n"
                f"Found: {len(df)} rows\nSample: {json.dumps(sample, default=str)[:1000]}"
            )
            tool_calls.append({
                "tool": "log_query",
                "date": day,
                "username": username,
                "result_count": int(len(df))
            })
            audit({
                "action": "tool_call",
                "user": user["sub"],
                "role": role,
                "tool": "log_query",
                "filters": {"date": day, "username": username},
                "result_count": int(len(df))
            })
        except Exception as e:
            audit({
                "action": "tool_error",
                "user": user["sub"],
                "role": role,
                "tool": "log_query",
                "error": str(e)
            })
            # Friendly 400 (client can show message) rather than 500
            raise HTTPException(status_code=400, detail="Log query failed")

    # ----- Retrieval (RAG) — tolerant even if Chroma has no vectors -----
    try:
        retrieved = retrieve_chunks(req.message, role=role, top_k=5)
    except Exception as e:
        audit({"action": "retrieval_unhandled_error", "error": str(e)})
        retrieved = []

    rag_context = ""
    for r in retrieved:
        src = (r.get("metadata") or {}).get("source_path", "unknown")
        rag_context += f"\n---\nSource: {src}\n{(r.get('text') or '')[:1000]}"

    # ----- LLM call with graceful offline fallback -----
    audit({
        "action": "llm_invoke",
        "user": user["sub"],
        "role": role,
        "prompt_excerpt": (req.message + rag_context + tool_section)[:400]
    })

    answer = llm_answer(req.message, rag_context, tool_section)  # tries OpenAI, falls back locally

    # Minimal DLP: redact long secret-y tokens
    answer = re.sub(r"[A-Za-z0-9_\-]{24,}", "[REDACTED]", answer)

    audit({
        "action": "llm_result",
        "user": user["sub"],
        "role": role,
        "result_excerpt": answer[:400]
    })

    return {"reply": answer, "retrieved": retrieved, "tool_calls": tool_calls}

    # (Optional) simple DLP mask for long tokens that look like secrets
    answer = re.sub(r"[A-Za-z0-9_\-]{24,}", "[REDACTED]", answer)

    audit({"action":"llm_result","user":user["sub"],"role":role,"result_excerpt":answer[:400]})
    return {"reply": answer, "retrieved": retrieved, "tool_calls": tool_calls}

class LogsQuery(BaseModel):
    date: Optional[str] = None  # "YYYY-MM-DD" (defaults to UTC today)
    username: Optional[str] = None
    limit: int = 200

@app.post("/logs/query")
def logs_query(req: LogsQuery, user=Depends(require_user)):
    role = user.get("role")
    if not role_allows_tool(role, "log_query"):
        raise HTTPException(status_code=403, detail="Your role is not authorized to query logs.")
    day = req.date or datetime.utcnow().date().isoformat()
    try:
        df = query_failed_logins(day, username=req.username, limit=req.limit)
        return {
            "date": day,
            "username": req.username,
            "result_count": int(len(df)),
            "rows": json.loads(df.to_json(orient="records", date_format="iso"))
        }
    except Exception as e:
        audit({"action": "tool_error", "tool": "log_query", "error": str(e)})
        raise HTTPException(status_code=400, detail="Log query failed")

