# app/agent/routing_config.py
"""
Configuration constants for semantic routing
"""

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
ROUTING_DB_PATH = PROJECT_ROOT / "data" / "routing_db"
CONFIG_FILE = PROJECT_ROOT / "config" / "routing_rules.yaml"

# Thresholds
SEMANTIC_SIMILARITY_THRESHOLD = 0.75  # Minimum similarity for semantic match
MIN_CONFIDENCE_THRESHOLD = 0.60        # Absolute minimum confidence
HIGH_CONFIDENCE_THRESHOLD = 0.85       # High confidence (no fallback needed)

# Performance
MAX_SEARCH_RESULTS = 3                 # Top K results to consider
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Same as RAG for consistency

# Default routing when all else fails
DEFAULT_ROUTE = {
    "use_rag": True,
    "use_logs": False,
    "use_web_search": False,
    "reason": "fallback:default-rag",
    "confidence": 0.3
}

# Category labels for logging/analytics
CATEGORIES = {
    "threat_intelligence": "Threat Intelligence / CVE Lookup",
    "authentication_logs": "Authentication Log Query",
    "policy_guidance": "Policy/Playbook Guidance",
    "logs_and_policy": "Combined: Logs + Policy",
    "threat_and_policy": "Combined: Threat Intel + Policy",
    "unknown": "Unknown/Uncategorized"
}
