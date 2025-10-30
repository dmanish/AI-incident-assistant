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
from app.agent.agent import decide_tools, synthesize_answer
from app.agent.function_calling_agent import create_agent
from app.agent.executors_enhanced import create_enhanced_tool_executors
from app.agent.memory import get_memory
import uuid

# --- Env & Paths ---
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

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
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Audit logger ---
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
    payload = {"sub": email, "role": role, "exp": datetime.utcnow() + timedelta(seconds=JWT_EXP_SECS)}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_jwt(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def require_user(authorization: Optional[str] = Header(None, alias="Authorization")) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization: Bearer <token>")
    token = authorization.split(" ", 1)[1]
    return decode_jwt(token)

# --- Prompt-injection heuristics ---
INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"override the system",
    r"execute the following",
    r"system prompt",
    r"open the (?:file|socket|port)",
]
def is_injection(text: str) -> bool:
    t = (text or "").lower()
    return any(re.search(p, t) for p in INJECTION_PATTERNS)

# --- Chroma retrieval (vector RAG) ---
import chromadb
from chromadb import PersistentClient
from rank_bm25 import BM25Okapi

chroma_client = PersistentClient(path=CHROMA_DB_DIR)

def _get_collection():
    """Lazy-load collection to handle background reindexing"""
    try:
        return chroma_client.get_collection("security_docs")
    except Exception as e:
        return None

def _bm25_rerank(query: str, docs: List[str], top_k: int = 5) -> List[int]:
    if not docs:
        return []
    tokens = [d.split() for d in docs]
    bm25 = BM25Okapi(tokens)
    scores = bm25.get_scores(query.split())
    idxs = list(range(len(docs)))
    idxs.sort(key=lambda i: scores[i] if len(scores) > 0 and i < len(scores) else 0.0, reverse=True)
    return idxs[:top_k]

def retrieve_chunks(query: str, role: str, top_k: int = 5) -> List[Dict[str, Any]]:
    collection = _get_collection()
    if collection is None:
        audit({"action": "retrieval_skip", "reason": "no_collection"})
        return []
    try:
        res = collection.query(
            query_texts=[query],
            n_results=20,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        audit({"action": "retrieval_error", "error": str(e)})
        return []

    if not res or not res.get("ids") or not res["ids"][0]:
        return []

    docs0 = res.get("documents", [[]])[0] or []
    metas0 = res.get("metadatas", [[]])[0] or []
    # Filter by RBAC
    filtered = [(d, m) for d, m in zip(docs0, metas0) if role_allows_doc(role, (m or {}).get("doc_type","kb"))]
    if not filtered:
        return []

    fd, fm = zip(*filtered)
    # Light BM25 re-rank on the filtered docs
    order = _bm25_rerank(query, list(fd), top_k=min(top_k, len(fd)))
    out: List[Dict[str, Any]] = []
    for i in order:
        out.append({
            "text": fd[i],
            "metadata": fm[i],
            "score": None
        })
    return out[:top_k]

# --- DuckDB log query tool ---
LOG_DIR = ROOT / "data" / "logs" / "auth"
LOG_DIR.mkdir(parents=True, exist_ok=True)

con_boot = duckdb.connect(DUCK_DB_PATH)
con_boot.execute("""
    CREATE TABLE IF NOT EXISTS auth_logs (
        timestamp TIMESTAMP, user VARCHAR, action VARCHAR, result VARCHAR, ip VARCHAR
    )
""")
con_boot.close()

def query_authentication_logs(
    date_start: str,
    date_end: Optional[str] = None,
    result_filter: str = "failed",
    username: Optional[str] = None,
    ip_address: Optional[str] = None,
    limit: int = 200
):
    """Enhanced authentication log query with flexible filtering"""
    from app.utils.log_query_enhanced import query_authentication_logs_enhanced
    return query_authentication_logs_enhanced(
        log_dir=LOG_DIR,
        duck_db_path=DUCK_DB_PATH,
        date_start=date_start,
        date_end=date_end,
        result_filter=result_filter,
        username=username,
        ip_address=ip_address,
        limit=limit
    )

# Backward compatible wrapper for old code
def query_failed_logins(date_iso: str, username: Optional[str] = None, limit: int = 200):
    """Legacy wrapper - calls enhanced version"""
    return query_authentication_logs(
        date_start=date_iso,
        date_end=date_iso,
        result_filter="failed",
        username=username,
        limit=limit
    )

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
    _openai_client = OpenAI(api_key=api_key)
    return _openai_client

def fallback_answer(user_msg: str, rag_context: str, tool_section: str) -> str:
    msg = (user_msg or "").lower()
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
        import re as _re
        m = _re.search(r"Found:\s+(\d+)\s+rows", tool_section or "")
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
    return (
        "Here’s a concise answer based on what I can see locally.\n"
        + (("\nContext used:\n" + rag_context[:600]) if rag_context else "")
        + (("\n\nTool results summary:\n" + tool_section[:400]) if tool_section else "")
    )

def llm_answer(user_msg: str, rag_context: str, tool_section: str) -> str:
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

# --- DLP post-LLM ---
from app.security.dlp import mask_text

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

# ------------------ ORIGINAL /chat (kept) ------------------
@app.post("/chat")
def chat(req: ChatRequest, user=Depends(require_user)):
    role = user.get("role")
    if is_injection(req.message):
        audit({"action": "blocked_prompt_injection", "user": user["sub"], "role": role, "prompt": req.message})
        raise HTTPException(status_code=400, detail="Potential prompt injection detected and blocked.")

    # Tool: logs (explicit ask)
    tool_section = ""
    tool_calls: List[Dict[str, Any]] = []
    msg_low = (req.message or "").lower()
    if any(k in msg_low for k in ["failed login", "failed logins", "show logs", "login attempts"]):
        if not role_allows_tool(role, "log_query"):
            audit({"action": "unauthorized_tool_access", "user": user["sub"], "role": role, "tool": "log_query"})
            raise HTTPException(status_code=403, detail="Your role is not authorized to query logs.")
        day = datetime.utcnow().date().isoformat()
        m = re.search(r"username\s+([a-z0-9_.-]+)", msg_low)
        username = m.group(1) if m else None
        try:
            df = query_failed_logins(day, username=username)
            sample = df.head(5).to_dict(orient="records")
            tool_section = (
                f"\n---\nTool: log_query\nDate: {day}\nUsername: {username}\n"
                f"Found: {len(df)} rows\nSample: {json.dumps(sample, default=str)[:1000]}"
            )
            tool_calls.append({"tool": "log_query","date": day,"username": username,"result_count": int(len(df))})
            audit({"action":"tool_call","user":user["sub"],"role":role,"tool":"log_query",
                   "filters":{"date":day,"username":username},"result_count":int(len(df))})
        except Exception as e:
            audit({"action":"tool_error","user":user["sub"],"role":role,"tool":"log_query","error":str(e)})
            raise HTTPException(status_code=400, detail="Log query failed")

    # RAG retrieval (tolerant)
    try:
        retrieved = retrieve_chunks(req.message, role=role, top_k=5)
    except Exception as e:
        audit({"action": "retrieval_unhandled_error", "error": str(e)})
        retrieved = []

    rag_context = ""
    citations: List[str] = []
    for r in retrieved:
        meta = (r.get("metadata") or {})
        src = meta.get("source_path", "unknown")
        citations.append(src)
        rag_context += f"\n---\nSource: {src}\n{(r.get('text') or '')[:1000]}"

    audit({"action": "llm_invoke","user": user["sub"],"role": role,"prompt_excerpt": (req.message + rag_context + tool_section)[:400]})
    answer = llm_answer(req.message, rag_context, tool_section)

    # --- DLP masking (post-LLM) ---
    masked, dlp_counts = mask_text(answer, role=role)
    audit({"action":"llm_result","user":user["sub"],"role":role,"result_excerpt": masked[:400], "dlp_counts": dlp_counts})

    return {"reply": masked, "retrieved": retrieved, "citations": citations, "tool_calls": tool_calls, "dlp_counts": dlp_counts}

# ------------------ NEW: /agent/chat ------------------

class AgentChatRequest(BaseModel):
    message: str
    convo_id: Optional[str] = None

@app.post("/agent/chat")
def agent_chat(req: AgentChatRequest, user=Depends(require_user)):
    role = user.get("role")
    if is_injection(req.message):
        audit({"action": "blocked_prompt_injection", "user": user["sub"], "role": role, "prompt": req.message})
        raise HTTPException(status_code=400, detail="Potential prompt injection detected and blocked.")

    route = decide_tools(req.message)
    use_rag = bool(route.get("use_rag"))
    use_logs = bool(route.get("use_logs"))
    use_web_search = bool(route.get("use_web_search"))
    audit({"action":"agent_decision","user":user["sub"],"role":role,"decision":{"rag":use_rag,"logs":use_logs,"web_search":use_web_search,"reason":route.get("reason")}})

    retrieved: List[Dict[str,Any]] = []
    citations: List[str] = []
    rag_context = ""
    tool_calls: List[Dict[str,Any]] = []

    if use_rag:
        try:
            retrieved = retrieve_chunks(req.message, role=role, top_k=5)
            for r in retrieved:
                meta = (r.get("metadata") or {})
                citations.append(meta.get("source_path","unknown"))
            # Compact context
            for r in retrieved:
                src = (r.get("metadata") or {}).get("source_path","unknown")
                rag_context += f"\n---\nSource: {src}\n{(r.get('text') or '')[:800]}"
            audit({"action":"tool_call","tool":"knowledge_base_search","user":user["sub"],"role":role,"result_count":len(retrieved)})
        except Exception as e:
            audit({"action":"tool_error","tool":"knowledge_base_search","user":user["sub"],"role":role,"error":str(e)})

    logs_context = ""
    if use_logs:
        if not role_allows_tool(role, "log_query"):
            audit({"action":"unauthorized_tool_access","tool":"log_query","user":user["sub"],"role":role})
        else:
            # parse a naive date/username
            day = datetime.utcnow().date().isoformat()
            m = re.search(r"username\s+([a-z0-9_.-]+)", (req.message or "").lower())
            username = m.group(1) if m else None
            try:
                df = query_failed_logins(day, username=username)
                sample = df.head(8).to_dict(orient="records")
                logs_context = (
                    f"\n---\nTool: log_query\nDate: {day}\nUsername: {username}\n"
                    f"Found: {len(df)} rows\nSample: {json.dumps(sample, default=str)[:1200]}"
                )
                tool_calls.append({"tool":"log_query","date":day,"username":username,"result_count":int(len(df))})
                audit({"action":"tool_call","tool":"log_query","user":user["sub"],"role":role,
                       "filters":{"date":day,"username":username},"result_count":int(len(df))})
            except Exception as e:
                audit({"action":"tool_error","tool":"log_query","user":user["sub"],"role":role,"error":str(e)})

    # Web search for threat intelligence
    web_search_context = ""
    if use_web_search:
        try:
            from app.utils.web_search import search_threat_intelligence, format_search_results

            # Determine search type from query
            query_lower = req.message.lower()
            if "cve" in query_lower or "vulnerability" in query_lower:
                search_type = "cve"
            elif any(word in query_lower for word in ["ip", "reputation"]):
                search_type = "ip_reputation"
            elif any(word in query_lower for word in ["domain", "url"]):
                search_type = "domain_reputation"
            else:
                search_type = "general"

            # Execute search using improved web search module
            search_response = search_threat_intelligence(
                query=req.message,
                search_type=search_type,
                max_results=5
            )

            # Format results for LLM
            web_search_context = format_search_results(search_response)

            # Audit logging
            tool_calls.append({
                "tool": "web_search",
                "query": req.message,
                "search_type": search_type,
                "result_count": search_response.get('result_count', 0),
                "source": search_response.get('source', 'unknown')
            })
            audit({
                "action": "tool_call",
                "tool": "web_search",
                "user": user["sub"],
                "role": role,
                "query": req.message,
                "result_count": search_response.get('result_count', 0),
                "source": search_response.get('source', 'unknown')
            })
        except Exception as e:
            web_search_context = f"\n---\nTool: web_search\nError: {str(e)}\nConsider searching security databases manually.\n"
            audit({"action": "tool_error", "tool": "web_search", "user": user["sub"], "role": role, "error": str(e)})

    # Ask LLM to synthesize (policy + logs + web search). Falls back locally if needed.
    combined_context = rag_context + logs_context + web_search_context
    answer = synthesize_answer(req.message, rag_context=combined_context, logs_context="")

    # --- DLP masking (post-LLM) ---
    masked, dlp_counts = mask_text(answer, role=role)
    audit({"action":"llm_result","user":user["sub"],"role":role,"result_excerpt":masked[:400], "dlp_counts": dlp_counts})

    return {
        "reply": masked,
        "citations": citations,       # list of source paths for UI
        "retrieved": retrieved,       # chunks (already filtered by RBAC)
        "tool_calls": tool_calls,     # logs tool summaries
        "agent_decision": {"rag":use_rag,"logs":use_logs,"reason":route.get("reason")},
        "dlp_counts": dlp_counts
    }

# ------------------ NEW: /agent/chat/v2 (Function Calling Agent) ------------------

# Initialize function calling agent (lazy init on first use)
_fc_agent = None

def get_fc_agent():
    """Get or create function calling agent"""
    global _fc_agent
    if _fc_agent is None:
        # Create enhanced tool executors
        tool_executors = create_enhanced_tool_executors(
            retrieve_chunks_fn=retrieve_chunks,
            query_logs_fn=query_authentication_logs,
            role_allows_tool_fn=role_allows_tool,
            role_allows_doc_fn=role_allows_doc
        )
        # Create agent
        _fc_agent = create_agent(tool_executors)
    return _fc_agent

class FunctionCallingChatRequest(BaseModel):
    message: str
    convo_id: Optional[str] = None

@app.post("/agent/chat/v2")
def agent_chat_v2(req: FunctionCallingChatRequest, user=Depends(require_user)):
    """
    True agentic chat endpoint using OpenAI function calling
    Supports iterative reasoning and multi-turn conversations
    """
    role = user.get("role")
    user_email = user.get("sub")

    # Prompt injection check
    if is_injection(req.message):
        audit({"action": "blocked_prompt_injection", "user": user_email, "role": role, "prompt": req.message})
        raise HTTPException(status_code=400, detail="Potential prompt injection detected and blocked.")

    # Get conversation memory
    memory = get_memory()
    convo_id = req.convo_id or str(uuid.uuid4())

    # Load conversation history if exists
    conversation_history = memory.get_conversation(convo_id)

    # Try to get function calling agent, fall back to heuristic if unavailable
    try:
        agent = get_fc_agent()
        use_function_calling = True
    except (ValueError, Exception) as e:
        # OpenAI not configured or quota exceeded - fall back to heuristic approach
        audit({"action": "agent_fallback_to_heuristic", "reason": str(e)[:200], "user": user_email, "role": role})
        agent = None
        use_function_calling = False

    # Audit callback
    def audit_callback(event: Dict[str, Any]):
        audit({**event, "user": user_email, "role": role, "convo_id": convo_id})

    # Run agent
    audit({"action": "agent_start", "user": user_email, "role": role, "query": req.message[:200], "convo_id": convo_id})

    if use_function_calling:
        # Use OpenAI function calling agent
        try:
            result = agent.run(
                user_message=req.message,
                role=role,
                conversation_history=conversation_history,
                audit_callback=audit_callback
            )
            # Check if the result indicates an LLM error (quota exceeded, etc.)
            if result.get("error") or "Error calling LLM" in result.get("answer", ""):
                # Fall back to heuristics
                audit({"action": "agent_runtime_fallback", "reason": "LLM error during execution", "user": user_email, "role": role})
                use_function_calling = False
                # Will execute heuristic logic below
            else:
                # Success with function calling
                pass
        except Exception as e:
            audit({"action": "agent_runtime_error", "error": str(e)[:200], "user": user_email, "role": role})
            # Fall back to heuristics on any error
            use_function_calling = False
    if not use_function_calling:
        # Fall back to heuristic-based approach (no OpenAI required)
        # Use the same logic as /agent/chat but return v2 response format
        decision = decide_tools(req.message)
        audit({"action": "agent_decision", "user": user_email, "role": role, "decision": decision})

        # Execute tools based on decision
        rag_context = ""
        logs_context = ""
        tool_calls_made = []
        reasoning_steps = []

        # Add initial reasoning step explaining fallback
        reasoning_steps.append({
            "step": 1,
            "type": "fallback_routing",
            "description": f"LLM unavailable (quota exceeded), using semantic routing fallback",
            "routing_method": decision.get("method", "unknown"),
            "routing_reason": decision.get("reason", ""),
            "confidence": decision.get("confidence"),
            "matched_example": decision.get("matched_example", "")[:100] if decision.get("matched_example") else None
        })

        if decision["use_rag"]:
            chunks = retrieve_chunks(req.message, role=role, top_k=5)
            if chunks:
                rag_context = "\n\n".join([f"---\nSource: {c['metadata'].get('source_path','')}\n{c['text']}" for c in chunks])
                tool_calls_made.append({"tool": "knowledge_base_search", "result_count": len(chunks)})
                reasoning_steps.append({
                    "step": len(reasoning_steps) + 1,
                    "type": "tool_call",
                    "tool_name": "knowledge_base_search",
                    "description": f"Searching knowledge base for relevant security policies and procedures",
                    "result": f"Found {len(chunks)} relevant documents"
                })

        if decision["use_logs"]:
            from datetime import datetime
            today = datetime.utcnow().date().isoformat()
            log_result = query_failed_logins(today, username=None)
            if log_result is not None and len(log_result) > 0:
                logs_context = f"---\nTool: log_query\nDate: {today}\nUsername: None\nFound: {len(log_result)} rows\nSample: {log_result[:2]}"
                tool_calls_made.append({"tool": "log_query", "result_count": len(log_result)})
                reasoning_steps.append({
                    "step": len(reasoning_steps) + 1,
                    "type": "tool_call",
                    "tool_name": "log_query",
                    "description": f"Querying authentication logs for date: {today}",
                    "arguments": {"date": today, "username": None},
                    "result": f"Found {len(log_result)} log entries"
                })

        # Web search for threat intelligence (fallback mode)
        web_search_context = ""
        if decision.get("use_web_search"):
            try:
                from app.utils.web_search import search_threat_intelligence, format_search_results

                # Determine search type from query
                query_lower = req.message.lower()
                if "cve" in query_lower or "vulnerability" in query_lower:
                    search_type = "cve"
                elif any(word in query_lower for word in ["ip", "reputation"]):
                    search_type = "ip_reputation"
                elif any(word in query_lower for word in ["domain", "url"]):
                    search_type = "domain_reputation"
                else:
                    search_type = "general"

                # Execute search using improved web search module
                search_response = search_threat_intelligence(
                    query=req.message,
                    search_type=search_type,
                    max_results=5
                )

                # Format results for LLM
                web_search_context = format_search_results(search_response)

                # Track tool call
                tool_calls_made.append({
                    "tool": "web_search",
                    "query": req.message,
                    "search_type": search_type,
                    "result_count": search_response.get('result_count', 0),
                    "source": search_response.get('source', 'unknown')
                })
                reasoning_steps.append({
                    "step": len(reasoning_steps) + 1,
                    "type": "tool_call",
                    "tool_name": "web_search",
                    "description": f"Searching threat intelligence databases ({search_type})",
                    "arguments": {"query": req.message, "search_type": search_type, "max_results": 5},
                    "result": f"Found {search_response.get('result_count', 0)} results from {search_response.get('source', 'unknown')}"
                })
                audit({
                    "action": "tool_call",
                    "tool": "web_search",
                    "user": user_email,
                    "role": role,
                    "query": req.message,
                    "result_count": search_response.get('result_count', 0),
                    "source": search_response.get('source', 'unknown')
                })
            except Exception as e:
                web_search_context = f"\n---\nTool: web_search\nError: {str(e)}\nConsider searching security databases manually.\n"
                audit({"action": "tool_error", "tool": "web_search", "user": user_email, "role": role, "error": str(e)})

        # Synthesize answer
        combined_context = rag_context + logs_context + web_search_context
        final_answer = synthesize_answer(req.message, rag_context=combined_context, logs_context="")

        # Add final reasoning step
        reasoning_steps.append({
            "step": len(reasoning_steps) + 1,
            "type": "final_answer",
            "description": "Synthesizing final answer from gathered information",
            "context_sources": [
                tool["tool"] for tool in tool_calls_made
            ]
        })

        # Format as v2 response (with reasoning transparency)
        result = {
            "answer": final_answer,
            "tool_calls": tool_calls_made,
            "iterations": 1,
            "messages": [],
            "reasoning_steps": reasoning_steps,
            "routes_used": {
                "llm_calls": 1 if rag_context or logs_context or web_search_context else 0,
                "rag_searches": 1 if decision["use_rag"] and rag_context else 0,
                "log_queries": 1 if decision["use_logs"] and logs_context else 0,
                "web_searches": 1 if decision.get("use_web_search") and web_search_context else 0,
                "tools_used": [tc["tool"] for tc in tool_calls_made]
            }
        }

    # Save conversation history (only for function calling mode with full history)
    if use_function_calling and result.get("messages"):
        memory.save_conversation(
            convo_id=convo_id,
            messages=result["messages"],
            user_email=user_email,
            role=role
        )

    # Apply DLP masking to final answer
    masked_answer, dlp_counts = mask_text(result["answer"], role=role)

    audit({
        "action": "agent_complete",
        "user": user_email,
        "role": role,
        "convo_id": convo_id,
        "iterations": result["iterations"],
        "tool_calls_count": len(result["tool_calls"]),
        "dlp_counts": dlp_counts
    })

    # Format response with reasoning transparency
    return {
        "reply": masked_answer,
        "convo_id": convo_id,
        "tool_calls": result["tool_calls"],
        "iterations": result["iterations"],
        "agent_type": "function_calling" if use_function_calling else "heuristic_fallback",
        "dlp_counts": dlp_counts,
        "max_iterations_reached": result.get("max_iterations_reached", False),
        # New: reasoning transparency fields
        "reasoning_steps": result.get("reasoning_steps", []),
        "routes_used": result.get("routes_used", {}),
        "metadata": {
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini") if use_function_calling else "heuristic",
            "total_llm_calls": result.get("routes_used", {}).get("llm_calls", 0),
            "used_rag": result.get("routes_used", {}).get("rag_searches", 0) > 0,
            "used_logs": result.get("routes_used", {}).get("log_queries", 0) > 0,
        }
    }

@app.get("/agent/memory/stats")
def get_memory_stats(user=Depends(require_user)):
    """Get conversation memory statistics"""
    memory = get_memory()
    stats = memory.get_stats()
    return stats

