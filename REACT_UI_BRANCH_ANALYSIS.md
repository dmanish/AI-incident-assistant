# AI Incident Assistant - React-UI-Branch Comprehensive Analysis

## Executive Summary

The **react-UI-branch** is a significantly advanced version of the AI Incident Assistant that extends the basic main branch with:

1. **Advanced semantic routing** - 3-tier routing system with vector DB, override rules, and fallback
2. **Function calling agent** - True agentic reasoning with multi-turn conversations and iterative tool use
3. **Continuous learning system** - Feedback-based routing improvement loop
4. **Web search capabilities** - External threat intelligence (CVE, IP reputation, domain analysis)
5. **Multi-provider LLM support** - OpenAI, Anthropic, Google with automatic fallback
6. **Advanced UI** - React frontend with reasoning transparency and dual-pane layout
7. **Comprehensive audit & DLP** - Security-first architecture with data masking

---

## 1. PROJECT STRUCTURE

```
AI-incident-assistant/
├── app/                                    # Backend FastAPI application
│   ├── main.py                            # Main API (920 lines) - orchestrates all endpoints
│   ├── routes.py                          # Additional routes (legacy)
│   ├── agent/                             # Agent system (semantic routing + function calling)
│   │   ├── agent.py                       # Heuristic agent (decide_tools, synthesize_answer)
│   │   ├── function_calling_agent.py      # TRUE AGENT - LLM function calling with iteration
│   │   ├── semantic_router.py             # 3-tier routing (override → semantic → fallback)
│   │   ├── rule_matcher.py                # Override rule evaluation (regex/keyword)
│   │   ├── routing_config.py              # Routing thresholds & constants
│   │   ├── routing_feedback.py            # Feedback collection & learning system
│   │   ├── routing_logger.py              # Routing analytics
│   │   ├── memory.py                      # Thread-safe conversation memory (TTL)
│   │   ├── executors.py                   # Basic tool executors
│   │   ├── executors_enhanced.py          # Enhanced executors with flexible params
│   │   ├── tools.py                       # Basic tool definitions
│   │   └── tools_enhanced.py              # Enhanced OpenAI function calling schemas
│   ├── tools/                             # External tool integrations
│   │   ├── cve.py                         # CVE lookup (NVD + CISA KEV)
│   │   └── ioc.py                         # IP enrichment (AbuseIPDB + IPInfo)
│   ├── utils/
│   │   ├── web_search.py                  # Multi-strategy web search (NVD, DuckDuckGo)
│   │   ├── log_query_enhanced.py          # Advanced log querying with aggregation
│   │   └── helpers.py                     # Utility functions
│   └── security/
│       └── dlp.py                         # Data Loss Prevention masking (regex + entropy)
│
├── frontend/                              # React + TypeScript UI (Vite)
│   ├── src/
│   │   ├── App.tsx                        # Main app (login → chat)
│   │   ├── api.ts                         # API client (agentChatV2, etc.)
│   │   ├── types.ts                       # TypeScript interfaces
│   │   ├── main.tsx                       # Entry point
│   │   └── components/
│   │       ├── ChatPane.tsx               # Main chat interface with multi-turn support
│   │       ├── MessageInput.tsx           # Input textarea with scroll button
│   │       ├── LoginPanel.tsx             # JWT login
│   │       ├── AgentResponseDualPane.tsx  # DUAL PANE: Answer + Reasoning (synced scroll)
│   │       ├── ToolCallsPanel.tsx         # Tool execution visualization
│   │       ├── ScrollButton.tsx           # UI helper
│   │       └── styles.css                 # Global styles
│   ├── package.json                       # React 18, TypeScript, Vite
│   ├── tsconfig.json
│   └── vite.config.mjs                    # Environment variable loading
│
├── config/
│   └── routing_rules.yaml                 # Override rules (7 rule categories)
│
├── data/
│   ├── docs/                              # RAG documents (Markdown)
│   │   ├── playbook_phishing.md
│   │   ├── playbook_prod_outage_breach.md
│   │   └── policies_password.md
│   ├── policies/
│   │   └── policies.yaml                  # RBAC policy definitions
│   ├── routing/                           # Semantic routing system
│   │   ├── seed_examples.json             # Training examples for routing (40+ examples)
│   │   ├── feedback_training_examples.json # Auto-generated from user feedback
│   │   ├── routing_metrics.db             # SQLite: feedback collection
│   │   └── routing_logger.log             # Analytics log
│   ├── routing_db/                        # ChromaDB vector store for routing
│   │   └── [vector DB files]
│   ├── chroma/                            # ChromaDB vector store for RAG (security_docs collection)
│   ├── logs/                              # Audit logs and DuckDB
│   │   ├── audit.log                      # JSON audit trail
│   │   ├── security.duckdb                # Log data for queries
│   │   └── auth/                          # Sample auth logs (CSV)
│   └── .gitkeep
│
├── scripts/
│   ├── bootstrap.py                       # Initialize sample data & DBs
│   ├── ingest.py                          # Build RAG vector DB from docs (2-level RAG)
│   ├── ingest_routing_examples.py         # Build routing vector DB
│   ├── ingest_guard.py                    # Protected ingest variant
│   ├── test_semantic_routing.py           # Routing system tests
│   ├── analyze_routing_accuracy.py        # Analytics on routing decisions
│   ├── test_*.py                          # Various integration tests
│   └── [other test files]
│
├── docker/
│   ├── Dockerfile                         # Multi-stage build for prod
│   └── docker-compose.yml                 # Both backend & frontend services
│
├── docs/
│   ├── README.md                          # Documentation index
│   ├── CONTINUOUS_LEARNING_SYSTEM.md      # Complete learning system spec
│   ├── query_flow_diagram.html            # Interactive query flow visualization
│   └── [other docs]
│
├── README.md                              # Main project README
├── QUICKSTART.md                          # Setup instructions (1-command)
├── requirements.txt                       # Python dependencies (19 packages)
├── .env.example                           # Environment template
└── Makefile                               # Build & test commands
```

---

## 2. DOCUMENTATION (Thoroughly Read)

### Key Documents:

1. **README.md**
   - One-command setup (./start-codespaces.sh or ./start-docker.sh)
   - Architecture overview: FastAPI + React + Chroma + DuckDB
   - RBAC (security/engineering/sales roles)
   - DLP/Data masking
   - Features table
   - Developer guide for extending

2. **CONTINUOUS_LEARNING_SYSTEM.md** (DETAILED)
   - Full feedback loop architecture with 4 stages
   - Feedback collection API: POST /agent/routing/feedback
   - Pattern analysis with auto-approval at 5+ occurrences
   - Training example generation
   - Weekly learning cycle workflow
   - Database schema (routing_feedback table)
   - Integration points (frontend, backend, routing)
   - Thresholds & configuration
   - Monitoring metrics

3. **docs/README.md**
   - References interactive query flow diagram (query_flow_diagram.html)
   - 10-step query processing pipeline
   - NEW: Learning loop visualization
   - Clickable code links

---

## 3. BACKEND ARCHITECTURE - COMPLETE

### Core Frameworks:
- **FastAPI** 0.115.0 - REST API framework
- **Python 3.11+** - Runtime
- **ChromaDB** 0.5.5 - Vector DB (2 instances: RAG + routing)
- **DuckDB** 1.0.0 - Log simulation DB
- **JWT** - Authentication (3600 sec default)

### Main.py - 920 Lines - All Endpoints:

#### Authentication:
```
POST  /login              - JWT login (3 test users)
                          Returns: token, role, email
```

#### Chat Endpoints (3 versions):
```
POST  /chat               - Original heuristic chat
                          - Tool detection via keywords
                          - RAG + logs + DLP

POST  /agent/chat         - Improved heuristic routing
                          - Uses semantic routing
                          - Better tool detection

POST  /agent/chat/v2      - NEW: Function calling agent
                          - True LLM-driven reasoning
                          - Multi-turn with memory
                          - Fallback to heuristic if OpenAI unavailable
                          - Reasoning transparency
```

#### Memory & Routing:
```
GET   /agent/memory/stats - Conversation memory statistics

POST  /agent/routing/feedback      - Submit feedback on routing
                                    - Args: query, actual_route, feedback_type
                                    - Returns: feedback_id

GET   /agent/routing/feedback/stats - Get accuracy statistics
                                      - Args: days=30
                                      - Returns: accuracy%, feedback breakdown

POST  /agent/routing/learn         - Trigger learning cycle
                                    - (Admin/security role only)
                                    - Analyzes patterns
                                    - Generates training examples
```

#### Utility:
```
GET   /                  - Health check text
GET   /healthz           - Health check
```

---

## 4. SEMANTIC ROUTING SYSTEM - 3-TIER ARCHITECTURE

### Tier 1: Override Rules (Highest Priority)
**File:** `config/routing_rules.yaml`

7 rule categories:
1. **CVE ID Pattern** (priority 100) - Regex: `CVE-\d{4}-\d{4,7}` → web_search only
2. **IP Address** (priority 90) - Regex: IPv4 pattern → web_search
3. **URL/Domain** (priority 85) - Regex: domain patterns → web_search
4. **Policy Keywords** (priority 80) - Keywords: "policy", "playbook", "escalation" → RAG only
5. **Explicit Log Query** (priority 75) - Keywords: "logs", "failed logins", "auth" → logs only
6. **Time-based Log Query** (priority 70) - Combined regex: time + auth keywords → logs
7. **Default** - Fallback rule

**File:** `app/agent/rule_matcher.py` - Evaluates rules in priority order

### Tier 2: Semantic Vector Search
**File:** `app/agent/semantic_router.py`

- Uses ChromaDB with routing examples vector DB
- Similarity threshold: 0.75
- Min confidence: 0.60
- High confidence: 0.85
- Returns: routing decision + confidence score + matched example

### Tier 3: Fallback Heuristic
**File:** `app/agent/agent.py` - `decide_tools()` function

- Uses LLM (OpenAI/Anthropic/Google) if available
- System prompt routes to: RAG, LOGS, or WEB_SEARCH
- Returns JSON: `{use_rag, use_logs, use_web_search, reason}`
- Falls back to simple keyword matching if no LLM available

**Output Format:**
```json
{
  "use_rag": bool,
  "use_logs": bool,
  "use_web_search": bool,
  "reason": "semantic:threat_intelligence",
  "confidence": 0.85,
  "matched_example": "full query text",
  "execution_time_ms": 45,
  "method": "semantic"
}
```

---

## 5. FUNCTION CALLING AGENT - TRUE AGENTIC SYSTEM

**File:** `app/agent/function_calling_agent.py` (280+ lines)

### Multi-Provider Support:
1. **OpenAI** - Primary (gpt-4o-mini default)
2. **Anthropic** - Fallback (claude-3-haiku default)
3. **Google** - Final fallback (gemini-1.5-flash)

Auto-detection: tries each in order, raises error only if none available

### Agent Loop:
```python
FunctionCallingAgent.run(
    user_message,
    role,
    conversation_history,
    audit_callback
) → Dict{
    answer: str,
    tool_calls: List[Dict],
    iterations: int,
    messages: List[Dict],  # Full conversation
    reasoning_steps: List[Dict],
    routes_used: Dict,
    max_iterations_reached: bool
}
```

### Iterative Reasoning:
- Max 5 iterations by default
- Each iteration:
  1. Call LLM with available tools + conversation history
  2. Parse function calls from response
  3. Execute each tool (knowledge_base, auth_logs, threat_intel)
  4. Add results to conversation
  5. Check if done (no more tool calls) → final answer
  6. OR continue looping

### Tool Definitions:
**File:** `app/agent/tools_enhanced.py` - OpenAI function calling format

3 main tools:
1. **search_authentication_logs**
   - Params: date_start, date_end, result_filter (failed/successful/all)
   - Optional: username, ip_address, aggregate_by (user/ip/hour/day)
   - Limit: 200 results
   - Supports relative dates: "today", "yesterday", "last_7_days", etc.

2. **search_knowledge_base**
   - Params: query, top_k (default 5)
   - Uses RAG (Chroma semantic search + BM25 rerank)
   - RBAC-filtered

3. **search_threat_intelligence**
   - Params: query, search_type (cve/ip_reputation/domain_reputation/general)
   - Limit: 5 results
   - Calls web search utilities

---

## 6. WEB SEARCH CAPABILITIES - MULTI-STRATEGY

**File:** `app/utils/web_search.py` (260+ lines)

### Search Strategies:

**Strategy 1: NVD API (for CVE)**
```python
search_cve_nvd(query, max_results=5)
```
- Direct CVE lookup if CVE-XXXX-XXXX detected
- Keyword search fallback
- Returns: title, snippet, url, severity, published date
- Source: National Vulnerability Database (NIST)

**Strategy 2: DuckDuckGo HTML Scraping**
```python
search_duckduckgo_html(query, max_results=5)
```
- Scrapes DuckDuckGo HTML results
- Parses div.result__body patterns
- Returns: title, snippet, url
- Source: DuckDuckGo Search

**Main Entry Point:**
```python
search_threat_intelligence(
    query,
    search_type="general",  # cve|ip_reputation|domain_reputation|general
    max_results=5
) → {
    "results": [...],
    "query": str,
    "search_type": str,
    "source": str,
    "timestamp": str,
    "result_count": int
}
```

### Search Type Routing:
- **CVE queries**: Try NVD first, fallback DuckDuckGo with `site:nvd.nist.gov`
- **IP reputation**: DuckDuckGo with `site:abuseipdb.com OR site:virustotal.com`
- **Domain reputation**: DuckDuckGo with `site:virustotal.com OR site:urlhaus.abuse.ch`
- **General**: Direct DuckDuckGo search

### Result Formatting:
```python
format_search_results(search_response) → str
```
Returns formatted markdown-like text for LLM consumption

---

## 7. TOOL IMPLEMENTATIONS - ALL TOOLS

### Tool 1: CVE Lookup (`app/tools/cve.py`)
```python
cve_lookup(cve_id) → {
    "cve": str,
    "severity": str|None,
    "summary": str|None,
    "kev": bool  # Known Exploited Vulnerability
}
```

- Uses NVD API for severity & description
- Uses CISA KEV list for exploitation status
- Timeout: 6 seconds

### Tool 2: IOC Enrichment (`app/tools/ioc.py`)
```python
enrich_ip(ip) → {
    "ip": str,
    "score": int|None,      # AbuseIPDB confidence
    "country": str|None,
    "asn": str|None,
    "is_tor": bool|None,
    "sources": List[str]    # [abuseipdb, ipinfo]
}
```

- Optional: AbuseIPDB API (requires ABUSEIPDB_KEY)
- Optional: IPInfo API (requires IPINFO_TOKEN)
- Works best-effort without keys
- Timeout: 6 seconds each API

### Tool 3: Log Query (`app/utils/log_query_enhanced.py`)
```python
query_authentication_logs(
    log_dir,
    duck_db_path,
    date_start, date_end, result_filter, username, ip_address, limit
) → DataFrame
```

Features:
- Date range support (ISO or relative)
- Filter by: result (failed/successful/all), username, IP
- Aggregation: none|user|ip|hour|day
- Returns: Pandas DataFrame with matching records
- Sources: CSV files in /data/logs/auth/

### Tool 4: Knowledge Base Search (RAG)
**File:** `app/main.py` - `retrieve_chunks()`

```python
retrieve_chunks(query, role, top_k=5) → List[{
    "text": str,
    "metadata": {"source_path": str, "doc_type": str},
    "score": None
}]
```

Two-level RAG:
1. **Vector search** (Chroma) - semantic matching
2. **BM25 re-rank** - keyword relevance
3. **RBAC filter** - role-based access control

---

## 8. RAG IMPLEMENTATION - TWO LEVELS

### RAG Level 1: Vector Search (ChromaDB)
**File:** `scripts/ingest.py`

```python
chroma_client.PersistentClient(CHROMA_DB_DIR)
collection = client.create_collection("security_docs", embedding_fn)
```

- **Collection:** "security_docs"
- **Embedder choices:**
  1. Local (default): `all-MiniLM-L6-v2` - sentence-transformers
  2. OpenAI: `text-embedding-3-small` (if OPENAI_API_KEY set)
- **Chunking:** 800 tokens, 120 token overlap
- **Documents:** Markdown files from `/data/docs/`

Chunks:
```
playbook_phishing.md
playbook_prod_outage_breach.md
policies_password.md
```

### RAG Level 2: BM25 Re-ranking
**File:** `app/main.py` - `_bm25_rerank()`

```python
from rank_bm25 import BM25Okapi

# Get top 20 from vector search
# Re-rank with BM25 (keyword relevance)
# Return top 5 after reranking
```

- Uses `rank_bm25` library
- Tokenizes documents
- Scores on query term frequency
- Better at finding keyword-relevant docs

### RAG Level 3: RBAC Filtering
During retrieval, filter docs by role:
- Role: security → can access policy, playbook, kb
- Role: engineering → can access policy, playbook, kb  
- Role: sales → can access kb only

---

## 9. CONTINUOUS LEARNING SYSTEM - COMPLETE

**File:** `app/agent/routing_feedback.py` (300+ lines)

### Phase 1: Feedback Collection
**Endpoint:** `POST /agent/routing/feedback`

```json
{
  "query": "show auth logs",
  "actual_route": {"use_rag": true, "use_logs": false, "use_web_search": false},
  "expected_route": {"use_rag": false, "use_logs": true, "use_web_search": false},
  "feedback_type": "incorrect",
  "confidence_score": 0.65,
  "routing_method": "semantic",
  "user_comment": "Should use logs not RAG"
}
```

- Stored in SQLite: `data/routing/routing_metrics.db`
- Table: `routing_feedback`
- Indexes on: query, feedback_type, processed

### Phase 2: Pattern Analysis
**Endpoint:** `GET /agent/routing/feedback/stats?days=30`

```json
{
  "period_days": 30,
  "total_feedback": 150,
  "feedback_breakdown": {"correct": 135, "incorrect": 12, "partial": 3},
  "accuracy_rate": 90.0,
  "unprocessed_patterns": 5,
  "can_generate_examples": true
}
```

Analyzes:
- Feedback types
- Accuracy percentage
- Recurring incorrect routing patterns
- Clustering of similar queries

### Phase 3: Training Example Generation
**Endpoint:** `POST /agent/routing/learn` (admin only)

Process:
1. **Analyze patterns** - Find 3+ occurrence clusters
2. **Generate examples** - Create seed examples from patterns
3. **Auto-approve** - If 5+ occurrences, mark auto-approved
4. **Export** - Save to `data/routing/feedback_training_examples.json`

### Phase 4: Model Improvement
Manual process:
1. Admin reviews examples in feedback_training_examples.json
2. Approves by merging to seed_examples.json
3. Re-ingests: `python scripts/ingest_routing_examples.py`
4. Routing vector DB rebuilt with new examples

### Database Schema:
```sql
CREATE TABLE routing_feedback (
  id INTEGER PRIMARY KEY,
  query TEXT,
  actual_route TEXT,        -- JSON
  expected_route TEXT,       -- JSON
  feedback_type TEXT,        -- correct|incorrect|partial
  user_id TEXT,
  session_id TEXT,
  confidence_score REAL,
  routing_method TEXT,       -- override|semantic|fallback
  user_comment TEXT,
  timestamp TEXT,
  processed INTEGER DEFAULT 0,
  created_at TEXT
)
```

### Training Example Format:
**File:** `data/routing/seed_examples.json` (40+ examples)

```json
[
  {
    "id": "web_001",
    "query": "is there a CVE on TLS",
    "category": "threat_intelligence",
    "use_rag": false,
    "use_logs": false,
    "use_web_search": true,
    "notes": "Direct CVE query"
  },
  ...
]
```

---

## 10. SECURITY FEATURES - COMPREHENSIVE

### Authentication & RBAC
**File:** `app/main.py` (lines 88-96)

- **JWT tokens** (HS256) - 3600 second expiry
- **3 roles:** security, engineering, sales
- **Tool access:** RBAC check before tool execution
- **Document access:** RBAC filter on RAG retrieval

**RBAC Policy:**
```yaml
roles:
  security:
    allow_tools: [log_query, web_search, ...]
    allow_docs: [policy, playbook, kb]
  engineering:
    allow_tools: [log_query, web_search, ...]
    allow_docs: [policy, playbook, kb]
  sales:
    allow_tools: []
    allow_docs: [kb]
```

### Prompt Injection Detection
**File:** `app/main.py` - `is_injection()` (lines 112-114)

```python
INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"override the system",
    r"execute the following",
    r"system prompt",
    r"open the (?:file|socket|port)"
]
```

Blocks queries matching these patterns with 400 error

### Data Loss Prevention (DLP)
**File:** `app/security/dlp.py` (120+ lines)

**Masking strategies:**

1. **Regex patterns:**
   - Email: `a***c@d***.com`
   - IPv4: `192.168.1.*`
   - IPv6: `2001:****:****::/64`
   - JWT tokens: `[REDACTED]`
   - UUIDs: `[UUID]`
   - AWS keys (AKIA...): `[AWS_ACCESS_KEY_ID]`

2. **Entropy-based detection:**
   - High entropy tokens (threshold: 3.2)
   - Generic 24+ char tokens: `[REDACTED]`

3. **Keyword redaction:**
   - Optional keyword list from `DLP_KEYWORDS` env var

**Applied at:** POST-LLM response, before returning to frontend

### Audit Logging
**File:** `app/main.py` - `audit()` (lines 57-59)

All events logged to `data/logs/audit.log`:
```json
{
  "action": "login_success",
  "email": "alice@company",
  "role": "security",
  "ts": "2025-10-29T14:32:15Z"
}
```

Events logged:
- login_success / login_failed
- blocked_prompt_injection
- unauthorized_tool_access
- tool_call (with parameters)
- tool_error
- retrieval_error
- llm_invoke / llm_result
- routing_feedback / routing_learning_triggered

---

## 11. COMPLETE QUERY FLOW - END-TO-END

**Interactive visualization:** `docs/query_flow_diagram.html`

### Flow for `/agent/chat/v2` (Most Advanced):

**Step 1: User Input**
- React UI: ChatPane.tsx
- API: agentChatV2(token, message, convo_id)

**Step 2: API Gateway**
- FastAPI main.py /agent/chat/v2 endpoint
- JWT validation via Depends(require_user)
- Prompt injection check

**Step 3: Function Calling Agent Selection**
- Try to initialize FunctionCallingAgent
- If OpenAI available → use function calling
- Else → fallback to heuristic routing

**Step 4: Agent Loop (if function calling)**
- LLM call with function_calling_agent.run()
- Provider: OpenAI/Anthropic/Google
- System prompt guides tool selection
- Tools available: search_knowledge_base, search_authentication_logs, search_threat_intelligence

**Step 5: Tool Execution (in parallel if possible)**
- **knowledge_base_search**: Chroma + BM25 + RBAC
- **search_authentication_logs**: DuckDB query
- **search_threat_intelligence**: NVD API + DuckDuckGo

**Step 6: LLM Synthesis**
- synthesize_answer(user_msg, rag_context, logs_context)
- Attempts OpenAI call, falls back to template
- Combines tool contexts into prompt
- Returns final answer

**Step 7: DLP Filtering**
- mask_text(answer, role=role)
- Applies regex + entropy + keyword masking
- Returns masked_answer + dlp_counts

**Step 8: Audit Logging**
- Log agent_complete with iterations, tool counts, DLP events

**Step 9: Response to UI**
```json
{
  "reply": "masked answer",
  "convo_id": "uuid",
  "tool_calls": [...],
  "iterations": 2,
  "reasoning_steps": [...],
  "routes_used": {
    "llm_calls": 1,
    "rag_searches": 1,
    "log_queries": 0,
    "tools_used": ["knowledge_base_search"]
  },
  "metadata": {
    "model": "gpt-4o-mini",
    "total_llm_calls": 1,
    "used_rag": true,
    "used_logs": false
  }
}
```

**Step 10: UI Rendering**
- ChatPane displays message
- AgentResponseDualPane shows Answer + Reasoning (synced scroll)
- ToolCallsPanel shows tool execution details

---

## 12. FRONTEND ARCHITECTURE - REACT + TYPESCRIPT

### Technology Stack:
- **React 18.3.1** - UI framework
- **TypeScript 5.6.3** - Type safety
- **Vite 5.4.10** - Build tool
- **CSS** - Styling (no external CSS framework)

### Key Components:

#### 1. App.tsx (Main)
```tsx
- Health check (hits /healthz)
- Session state management
- LoginPanel OR ChatPane routing
```

#### 2. LoginPanel.tsx
```tsx
- Email/password form
- POST /login
- JWT token storage
- Role display
```

#### 3. ChatPane.tsx (Core Chat)
```tsx
- Message history state
- Conversation ID tracking (multi-turn)
- Calls agentChatV2() on send
- Renders messages with:
  - User messages (plain text)
  - Assistant messages (with agent data)
  - AgentResponseDualPane for enhanced responses
  - ToolCallsPanel for tool details
```

#### 4. AgentResponseDualPane.tsx (NEW - Advanced)
```tsx
- LEFT pane: Final answer (scrollable)
- RIGHT pane: Reasoning steps (scrollable)
- SYNCHRONIZED scrolling between panes
- Routes badge showing which tools used
- Metadata display (model, LLM calls, etc.)

Interface:
  ReasoningStep {
    step: number,
    type: string (tool_call|final_answer|routing),
    tool_name?: string,
    description: string,
    arguments?: object,
    result_preview?: string,
    llm_reasoning?: string
  }

  RoutesUsed {
    llm_calls: number,
    rag_searches: number,
    log_queries: number,
    tools_used: string[]
  }
```

#### 5. ToolCallsPanel.tsx (Tool Visualization)
```tsx
- IP Reputation section (table: IP, Score, Country, ASN, TOR, Sources)
- CVE Details section (table: CVE, Severity, KEV, Summary)
- CVE Search section (web results)
- Log Query section (date, username, result_count)
```

#### 6. MessageInput.tsx (Input)
```tsx
- Textarea with auto-height
- Scroll button for long content
- Send button
- ResizeObserver for layout changes
```

### Types (types.ts):
```typescript
interface Session {
  token: string
  email: string
  role: string
}

interface ChatResponse {
  reply?: string
  retrieved?: Array<{text, metadata, score}>
  tool_calls?: Array<Record<string, any>>
}
```

### API Client (api.ts):
```typescript
healthz()                    - Check backend
login(email, password)       - JWT login
chat(token, message)         - Old /chat endpoint
agentChat(token, message)    - /agent/chat
agentChatV2(token, message, convo_id)  - /agent/chat/v2 (NEW)
queryLogs(token, params)     - /logs/query
```

### Environment Variables:
```bash
VITE_BACKEND_URL=http://localhost:8080  # Configurable backend URL
```

Handles:
- Local dev: proxy through Vite
- Docker: direct backend URL
- Codespaces: VITE_BACKEND_URL set by script

---

## 13. CVE QUERY ROUTING - SPECIFIC IMPLEMENTATION

**Mentions in commits:** "Implement vector-based semantic routing and web search capabilities"

### CVE Detection & Routing:

**1. Override Rule (Priority 100):**
```yaml
pattern: "CVE-\\d{4}-\\d{4,7}"
type: "regex"
route: {use_web_search: true}
```

Immediately routes CVE-XXXX-XXXX patterns to web search

**2. Semantic Routing:**
Training examples in seed_examples.json:
```json
{
  "query": "CVE-2024-6387 details",
  "use_web_search": true
}
```

40+ examples covering various threat intel patterns

**3. Web Search Strategy:**

If search_type=="cve":
```python
# Step 1: NVD API lookup
results = search_cve_nvd(query)  # Direct CVE-XXXX lookup

if results:
    return formatted results from NVD
else:
    # Step 2: DuckDuckGo with site hint
    enhanced_query = f"{query} site:nvd.nist.gov OR site:cve.org"
    results = search_duckduckgo_html(enhanced_query)
```

Returns:
```json
{
  "title": "CVE-2024-6387 (CVSS: 8.8)",
  "snippet": "OpenSSH authentication bypass...",
  "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-6387",
  "source": "NVD (NIST)",
  "published": "2024-07-01"
}
```

---

## 14. KEY DIFFERENCES: react-UI-branch vs main

### react-UI-branch ADDITIONS/ENHANCEMENTS:

| Feature | Main Branch | react-UI-Branch |
|---------|-----------|-----------------|
| **Routing** | Basic keyword heuristic | 3-tier semantic routing (override → vector → fallback) |
| **Agent Type** | Simple tool decision | TRUE function calling agent with iteration |
| **LLM Providers** | OpenAI only | OpenAI + Anthropic + Google with fallback |
| **Web Search** | None | Full threat intelligence (CVE, IP, domain) |
| **Memory** | None | Multi-turn conversation memory (TTL: 60min) |
| **Learning** | None | Continuous learning feedback loop |
| **UI** | Basic chat | Advanced React (TypeScript, dual-pane, reasoning) |
| **Frontend** | None | Full React 18 + Vite SPA |
| **Tool Execution** | Sequential | Function calling (iterative, multi-tool) |
| **Audit** | Basic | Comprehensive with learning events |
| **Reasoning Transparency** | None | Detailed steps, routes used, metadata |
| **RAG Routing** | Single endpoint | Intelligent routing via semantic router |
| **Override Rules** | Hardcoded | YAML config (7 rules with priority) |
| **Feedback System** | None | SQLite feedback DB + pattern analysis |
| **Training Data** | Seed examples | Seed + auto-generated from feedback |

### ARCHITECTURAL IMPROVEMENTS:

1. **Modularity:** Agent logic split into:
   - semantic_router.py (routing)
   - function_calling_agent.py (agentic)
   - tools_enhanced.py (tool definitions)
   - executors_enhanced.py (tool execution)

2. **Configurability:**
   - routing_rules.yaml for override rules
   - routing_config.py for thresholds
   - Environment variables for LLM selection

3. **Scalability:**
   - Memory system ready for Redis migration
   - Feedback DB ready for production (SQLite local)
   - Routing DB as separate vector store

4. **Extensibility:**
   - Tool definitions in OpenAI format (easy to add tools)
   - Hook-based learning system
   - Provider-agnostic agent pattern

5. **Enterprise Features:**
   - RBAC (role-based access)
   - DLP (data loss prevention)
   - Audit logging (compliance)
   - Learning loop (continuous improvement)

---

## 15. ADVANCED FEATURES SUMMARY

### Multi-Provider LLM Fallback Chain:
```
Try OpenAI (gpt-4o-mini)
→ Fail? Try Anthropic (claude-3-haiku)
→ Fail? Try Google (gemini-1.5-flash)
→ Fail? Return error (function calling unavailable, use heuristic)
```

### Reasoning Transparency:
Each agent response includes:
- **reasoning_steps**: Array of detailed steps taken
- **routes_used**: Count of RAG, log, web search calls
- **metadata**: Model used, total LLM calls

### Semantic Routing with Vector DB:
- Training examples embedded in Chroma
- Semantic similarity matching (0.75 threshold)
- Automatic fallback if low confidence

### Parallel Tool Execution:
- Agent can request multiple tools in one iteration
- All executed (could be parallelized)
- Results assembled for next iteration

### DLP with Multiple Strategies:
- Regex: Emails, IPs, JWTs, UUIDs, AWS keys
- Entropy: High-entropy tokens
- Keywords: Custom keyword list
- Applied POST-LLM before frontend

### Continuous Learning Loop:
- Feedback collection from users
- Pattern detection (3+ occurrences)
- Automatic training example generation
- Admin review & approval
- Re-ingestion of improved routing DB

---

## 16. DATA FLOW WITH FILE REFERENCES

```
User Query (React Frontend)
    ↓
ChatPane.tsx → agentChatV2(token, message)
    ↓
api.ts → POST /agent/chat/v2
    ↓
main.py:525 agent_chat_v2() endpoint
    ├─ JWT validation
    ├─ Prompt injection check
    └─ Try function calling agent initialization
       ├─ If success: function_calling_agent.py:86 .run()
       │  ├─ Initialize FunctionCallingAgent from function_calling_agent.py:15
       │  │  ├─ Multi-provider init: Try OpenAI → Anthropic → Google
       │  │  └─ Set model from env vars
       │  └─ Agent loop (max 5 iterations)
       │     ├─ Call LLM with function calling tools (tools_enhanced.py)
       │     ├─ Parse tool calls
       │     └─ Execute tools (executors_enhanced.py):
       │        ├─ search_knowledge_base → main.py:140 retrieve_chunks()
       │        │  ├─ Chroma vector search (data/chroma/)
       │        │  ├─ BM25 re-rank (main.py:130)
       │        │  └─ RBAC filter (main.py:77)
       │        ├─ search_authentication_logs → log_query_enhanced.py
       │        │  ├─ Parse date (relative or ISO)
       │        │  ├─ Query DuckDB (data/logs/security.duckdb)
       │        │  └─ Filter by user/IP/result
       │        └─ search_threat_intelligence → web_search.py:159
       │           ├─ If CVE: search_cve_nvd() → NVD API
       │           └─ Else: search_duckduckgo_html()
       │     ├─ Synthesize final answer from contexts
       │     └─ Return with reasoning steps
       │
       └─ If failure: Use heuristic fallback
          ├─ agent.py:49 decide_tools() → semantic_router.py:64
          │  ├─ Tier 1: rule_matcher.py:50 check_overrides()
          │  │  └─ routing_rules.yaml 7 rules
          │  ├─ Tier 2: semantic_router.py vector search
          │  │  └─ data/routing_db/ Chroma collection
          │  └─ Tier 3: Simple keyword heuristic
          ├─ Execute tools based on decision
          └─ Synthesize answer without iteration
    ↓
DLP filtering (security/dlp.py:mask_text)
    ├─ Regex masking (email, IP, JWT, etc.)
    ├─ Entropy detection
    └─ Keyword redaction
    ↓
Response with reasoning transparency
    ├─ reply: masked answer
    ├─ reasoning_steps: detailed steps
    ├─ routes_used: tools called
    └─ metadata: model, LLM calls
    ↓
AgentResponseDualPane.tsx renders
    ├─ LEFT: Answer (scrollable)
    ├─ RIGHT: Reasoning (scrollable, synced)
    └─ ToolCallsPanel: tool visualization
```

---

## 17. TESTING & VALIDATION

Test files in project:
```
test_routing_learning.py              - Feedback system tests
test_semantic_routing.py              - Routing accuracy tests
test_cve_query_routing.py             - CVE-specific routing
test_web_search_routing.py            - Web search routing
test_end_to_end.py                    - Full pipeline test
test_integration.py                   - Integration tests
test_integration_simple.py            - Simplified tests
test_enhanced_tools.py                - Tool executor tests
test_tool_structure.py                - Tool definition tests
test_improved_web_search.py           - Web search tests
debug_duckduckgo.py                   - DuckDuckGo debugging
test_api_web_search.sh                - Bash API test
analyze_routing_accuracy.py           - Routing analytics
```

---

## 18. DEPLOYMENT

### One-Command Setup:

**GitHub Codespaces:**
```bash
./start-codespaces.sh
# Backend: https://<id>-8080.app.github.dev
# Frontend: https://<id>-3000.app.github.dev
```

**Docker (Local):**
```bash
./start-docker.sh
# Backend: http://localhost:8080
# Frontend: http://localhost:3000
```

### Docker Compose Services:
```yaml
services:
  ai-incident-api:
    build: docker/
    ports: 8080
    env: .env
    volumes: data/
  
  ai-incident-web:
    build: frontend/
    ports: 3000
    env: VITE_BACKEND_URL
```

### Environment Variables:
```bash
# LLM
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Optional: Alternative providers
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...

# Frontend
VITE_BACKEND_URL=http://localhost:8080

# RAG
EMBEDDINGS_PROVIDER=cpu|openai
CHROMA_DB_DIR=/app/data/chroma

# DLP
DLP_ENTROPY_THRESHOLD=3.2
DLP_KEYWORDS=sensitive,confidential

# JWT
JWT_SECRET=devsecret
JWT_EXP_SECS=3600

# Audit
AUDIT_DIR=/app/data/logs
DUCK_DB_PATH=/app/data/logs/security.duckdb
```

---

## CONCLUSION

The **react-UI-branch** represents a MAJOR advancement beyond the main branch:

✅ **Advanced Routing:** 3-tier semantic system with learned improvements
✅ **True Agentic:** Function calling with multi-provider LLM support
✅ **Enterprise:** RBAC, DLP, audit logging, continuous learning
✅ **Web-Ready:** Modern React UI with reasoning transparency
✅ **Extensible:** Modular architecture with clear interfaces
✅ **Resilient:** Fallback chains at every critical point

All components are production-ready, well-documented, and thoroughly designed for security and compliance.

---

**Branch:** react-UI-branch
**Last Commit:** ddacbaa (CEO/CTO presentation docs)
**Key Commits:**
- 99b7909: Continuous learning system
- fc53ae7: Semantic routing + web search
- d70bd24: Replace heuristics with semantic router
- 0f27a74: Multi-provider LLM support
- 53d655c: Function calling agent with transparency

