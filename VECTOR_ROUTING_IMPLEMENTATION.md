# Vector-Based Semantic Routing Implementation

## Overview

This document tracks the complete refactoring from keyword-based heuristic routing to vector-based semantic routing with ChromaDB.

---

## STEP 1: CLEANUP - Remove Existing Heuristics (TO BE COMMITTED)

### Files Modified:
1. `app/agent/agent.py` - Remove keyword-based heuristics
2. `app/agent/semantic_router.py` - New module (created)

### Changes:

#### Before (Keyword-based):
```python
# app/agent/agent.py - decide_tools()
web_search_signals = any(s in t for s in [
    "cve", "vulnerability", "exploit", ...
])
logs_signals = any(s in t for s in [
    "login", "failed", "auth", ...
])
# Lots of hardcoded keyword lists
```

#### After (Prepared for semantic):
```python
# app/agent/agent.py - decide_tools()
# Delegates to semantic router
from app.agent.semantic_router import SemanticRouter
router = SemanticRouter()
return router.route(user_msg)
```

---

## STEP 2: PHASE 0 - Vector DB Ingestion (NOT TO BE COMMITTED YET)

### Purpose:
Extract existing routing patterns from audit logs and seed the vector DB.

### Files Created:
1. `scripts/ingest_routing_examples.py` - Main ingestion script
2. `data/routing/seed_examples.json` - Manual seed examples
3. `data/routing/extracted_patterns.json` - Auto-extracted from logs

### Process:
1. **Manual Seed (50-100 examples):**
   - Hand-crafted examples for each tool
   - High-quality, diverse phrasings

2. **Audit Log Mining:**
   - Parse `data/logs/audit.log`
   - Extract queries with `agent_decision` events
   - Filter for successful routings
   - Deduplicate similar queries

3. **Vector DB Population:**
   - Create ChromaDB collection: `routing_examples`
   - Embed using `all-MiniLM-L6-v2` (same as RAG)
   - Store with metadata: `{use_rag, use_logs, use_web_search, category}`

### Schema:
```python
{
    "id": "route_001",
    "query": "is there a CVE on TLS",
    "embedding": [0.23, -0.45, ...],  # ChromaDB handles this
    "metadata": {
        "use_rag": False,
        "use_logs": False,
        "use_web_search": True,
        "category": "threat_intelligence",
        "added_date": "2025-10-29",
        "source": "manual_seed"  # or "audit_log"
    }
}
```

---

## STEP 3: PHASE 1 - Semantic Routing Foundation (NOT TO BE COMMITTED YET)

### Files Created:
1. `app/agent/semantic_router.py` - Main routing logic
2. `app/agent/routing_config.py` - Configuration constants

### Implementation:

```python
class SemanticRouter:
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(path="./data/routing_db")
        self.collection = self.chroma_client.get_collection("routing_examples")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.similarity_threshold = 0.75

    def route(self, query: str) -> Dict[str, Any]:
        """
        Route query using semantic similarity

        Returns:
            {
                "use_rag": bool,
                "use_logs": bool,
                "use_web_search": bool,
                "reason": str,
                "confidence": float,
                "matched_example": str
            }
        """
        # Step 1: Embed query
        query_embedding = self.embedder.encode(query)

        # Step 2: Search vector DB
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=3
        )

        # Step 3: Check similarity threshold
        if results['distances'][0][0] < (1 - self.similarity_threshold):
            # High confidence match
            metadata = results['metadatas'][0][0]
            return {
                "use_rag": metadata['use_rag'],
                "use_logs": metadata['use_logs'],
                "use_web_search": metadata['use_web_search'],
                "reason": f"semantic:{metadata['category']}",
                "confidence": 1 - results['distances'][0][0],
                "matched_example": results['documents'][0][0]
            }
        else:
            # Fall back to config file or default
            return self._config_fallback(query)
```

### Performance Target:
- Embedding: 30-50ms
- ChromaDB lookup: 10-20ms
- **Total: <70ms** (vs 500-1500ms LLM routing)

---

## STEP 4: PHASE 2 - Config File Overrides (NOT TO BE COMMITTED YET)

### Files Created:
1. `config/routing_rules.yaml` - Override rules
2. `app/agent/rule_matcher.py` - Rule evaluation logic

### Config Structure:
```yaml
# config/routing_rules.yaml
version: "1.0"

# Critical patterns that override semantic routing
overrides:
  - name: "explicit_cve_id"
    pattern: "CVE-\\d{4}-\\d{4,7}"
    type: "regex"
    priority: 100
    route:
      use_rag: false
      use_logs: false
      use_web_search: true
    reason: "override:cve-id-pattern"

  - name: "ip_address_query"
    pattern: "\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b"
    type: "regex"
    priority: 90
    route:
      use_rag: false
      use_logs: false
      use_web_search: true
    reason: "override:ip-address"

  - name: "explicit_policy_request"
    keywords: ["policy", "playbook", "procedure"]
    require_all: false
    priority: 80
    route:
      use_rag: true
      use_logs: false
      use_web_search: false
    reason: "override:policy-keywords"

# Default when no match found
default:
  use_rag: true
  use_logs: false
  use_web_search: false
  reason: "fallback:default-rag"

# Thresholds
thresholds:
  semantic_similarity: 0.75
  min_confidence: 0.60
```

### Enhanced Router:
```python
class SemanticRouter:
    def route(self, query: str):
        # Step 1: Check config overrides FIRST
        override = self.rule_matcher.check_overrides(query)
        if override:
            return override

        # Step 2: Semantic vector search
        result = self._vector_search(query)
        if result['confidence'] > self.similarity_threshold:
            return result

        # Step 3: Default fallback from config
        return self.config['default']
```

---

## STEP 5: PHASE 3 - Continuous Improvement (NOT TO BE COMMITTED YET)

### Files Created:
1. `scripts/analyze_routing_accuracy.py` - Analytics script
2. `data/routing/routing_metrics.db` - SQLite tracking DB
3. `app/agent/routing_logger.py` - Enhanced logging

### Logging Schema:
```sql
CREATE TABLE routing_decisions (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    query TEXT,
    route_decision JSON,  -- {use_rag, use_logs, use_web_search}
    method TEXT,  -- 'semantic' | 'override' | 'default'
    confidence FLOAT,
    matched_example TEXT,
    user_feedback TEXT,  -- Optional feedback
    execution_time_ms INTEGER
);
```

### Logged Data:
```python
audit({
    "action": "semantic_routing_decision",
    "query": user_msg[:200],
    "decision": {
        "use_rag": result['use_rag'],
        "use_logs": result['use_logs'],
        "use_web_search": result['use_web_search']
    },
    "method": result['reason'].split(':')[0],  # semantic/override/fallback
    "confidence": result.get('confidence', 0),
    "matched_example": result.get('matched_example', '')[:100],
    "execution_time_ms": elapsed_ms
})
```

### Analytics Queries:

1. **Low Confidence Routes:**
```sql
SELECT query, confidence, route_decision
FROM routing_decisions
WHERE confidence < 0.75 AND method = 'semantic'
ORDER BY confidence ASC
LIMIT 100;
```

2. **Most Common Queries:**
```sql
SELECT query, COUNT(*) as count, AVG(confidence) as avg_conf
FROM routing_decisions
GROUP BY query
ORDER BY count DESC
LIMIT 50;
```

3. **Route Distribution:**
```sql
SELECT
    JSON_EXTRACT(route_decision, '$.use_rag') as rag,
    JSON_EXTRACT(route_decision, '$.use_logs') as logs,
    JSON_EXTRACT(route_decision, '$.use_web_search') as web,
    COUNT(*) as count
FROM routing_decisions
GROUP BY rag, logs, web;
```

### Improvement Script:
```python
# scripts/analyze_routing_accuracy.py
def suggest_new_examples():
    """
    Analyze logs and suggest new training examples
    """
    # Find low confidence queries
    low_conf = get_low_confidence_queries()

    # Cluster similar queries
    clusters = cluster_queries(low_conf)

    # Suggest representative examples
    for cluster in clusters:
        print(f"Add example: {cluster['representative']}")
        print(f"  Similar queries: {len(cluster['members'])}")
        print(f"  Suggested route: {cluster['most_common_route']}")
```

---

## PHASE 4: A/B Testing (Optional - NOT IMPLEMENTED YET)

### Concept:
Run both keyword and vector routing in parallel for 1 week:
- 50% traffic → keyword routing
- 50% traffic → vector routing
- Compare accuracy metrics
- Measure which correctly routes more queries

### Implementation (Future):
```python
def route_with_ab_test(query: str):
    # Route with both methods
    keyword_result = keyword_route(query)
    vector_result = semantic_route(query)

    # Log both for comparison
    audit({
        "action": "ab_test_routing",
        "keyword": keyword_result,
        "vector": vector_result,
        "agreement": keyword_result == vector_result
    })

    # Return based on A/B bucket
    user_bucket = hash(user_id) % 2
    return vector_result if user_bucket == 0 else keyword_result
```

---

## Summary of Changes

### Cleanup Commit (Step 1):
- Remove keyword heuristics from `agent.py`
- Create `semantic_router.py` stub
- Update imports

### Phase 0-3 Implementation (NOT COMMITTED):
- Seed vector DB with 100+ examples
- Implement semantic routing
- Add config file overrides
- Enhanced logging and analytics

### Files Changed:
**Modified:**
- `app/agent/agent.py` (cleaned heuristics)
- `app/main.py` (use semantic router)
- `scripts/bootstrap.py` (call routing ingest)

**Created:**
- `app/agent/semantic_router.py`
- `app/agent/routing_config.py`
- `app/agent/rule_matcher.py`
- `app/agent/routing_logger.py`
- `config/routing_rules.yaml`
- `data/routing/seed_examples.json`
- `scripts/ingest_routing_examples.py`
- `scripts/analyze_routing_accuracy.py`

### Performance Comparison:

| Method | Latency | Accuracy | Cost | Reliability |
|--------|---------|----------|------|-------------|
| **LLM Routing** | 500-1500ms | 95% | $0.001/query | Depends on quota |
| **Keyword Heuristics** | <5ms | 70% | Free | High |
| **Vector Semantic** | 60-70ms | 90%* | Free | High |

*After sufficient training examples

### Testing Checklist:

- [ ] Vector DB populated with 100+ examples
- [ ] Semantic routing returns results <100ms
- [ ] Override rules fire correctly
- [ ] Low confidence queries fall back to default
- [ ] All routing decisions logged with confidence scores
- [ ] Analytics script identifies improvement areas
- [ ] No regression in RAG/logs/web search functionality

---

## Migration Path:

1. **Week 1:** Deploy with high threshold (0.85) - conservative
2. **Week 2:** Analyze logs, add 50 new examples from real queries
3. **Week 3:** Lower threshold to 0.75, monitor accuracy
4. **Week 4:** Add config overrides for any edge cases
5. **Ongoing:** Monthly review of low-confidence queries

---

*This document will be updated as implementation progresses.*

**Status: In Progress**
**Last Updated: 2025-10-29**
