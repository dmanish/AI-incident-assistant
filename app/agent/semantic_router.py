# app/agent/semantic_router.py
"""
Semantic routing using vector similarity instead of keyword matching
Routes user queries to appropriate tools based on semantic meaning

Phase 1 Implementation: Vector DB with ChromaDB
Phase 3 Integration: Continuous improvement logging
"""

from typing import Dict, Any, Optional
import chromadb
from pathlib import Path
import time
from .routing_config import (
    ROUTING_DB_PATH,
    SEMANTIC_SIMILARITY_THRESHOLD,
    MIN_CONFIDENCE_THRESHOLD,
    HIGH_CONFIDENCE_THRESHOLD,
    MAX_SEARCH_RESULTS,
    DEFAULT_ROUTE,
    CATEGORIES
)
from .rule_matcher import get_matcher


class SemanticRouter:
    """
    Routes queries using semantic similarity with ChromaDB
    Falls back to config-based rules when needed
    """

    def __init__(self):
        """
        Initialize the semantic router with vector DB
        """
        self.client = None
        self.collection = None
        self.initialized = False
        self.fallback_enabled = True

        # Try to initialize ChromaDB
        try:
            self._initialize_chroma()
        except Exception as e:
            print(f"Warning: Could not initialize semantic router: {e}")
            print("Falling back to simple routing")

    def _initialize_chroma(self):
        """Initialize ChromaDB client and collection"""
        if not ROUTING_DB_PATH.exists():
            print(f"Warning: Routing DB not found at {ROUTING_DB_PATH}")
            print("Run 'python scripts/ingest_routing_examples.py' to create it")
            return

        try:
            self.client = chromadb.PersistentClient(path=str(ROUTING_DB_PATH))
            self.collection = self.client.get_collection("routing_examples")
            self.initialized = True
            print(f"✓ Semantic router initialized with {self.collection.count()} examples")
        except Exception as e:
            print(f"Warning: Could not load routing collection: {e}")
            self.initialized = False

    def route(self, user_msg: str, log_decision: bool = True) -> Dict[str, Any]:
        """
        Route a user query to appropriate tools using semantic similarity

        Three-tier routing:
        1. Check config override rules (regex/keyword patterns)
        2. Semantic vector search (if initialized)
        3. Simple fallback (minimal keywords)

        Args:
            user_msg: User's query text
            log_decision: Whether to log this decision (default True)

        Returns:
            Dict with:
                - use_rag: bool
                - use_logs: bool
                - use_web_search: bool
                - reason: str (e.g., "semantic:threat_intelligence")
                - confidence: float (0-1)
                - matched_example: str (optional)
                - execution_time_ms: int (optional)
                - method: str (override/semantic/fallback)
        """
        start_time = time.time()

        # TIER 1: Check override rules first (highest priority)
        try:
            matcher = get_matcher()
            override_result = matcher.check_overrides(user_msg)
            if override_result:
                override_result['execution_time_ms'] = int((time.time() - start_time) * 1000)
                self._log_decision(user_msg, override_result, log_decision)
                return override_result
        except Exception as e:
            print(f"Warning: Override check failed: {e}")
            # Continue to semantic search

        # TIER 2: Semantic vector search
        if self.initialized and self.collection is not None:
            try:
                result = self._semantic_search(user_msg)
                result['execution_time_ms'] = int((time.time() - start_time) * 1000)
                result['method'] = 'semantic'
                self._log_decision(user_msg, result, log_decision)
                return result
            except ValueError as e:
                # Low similarity - expected fallback to keyword detection
                # Fall through to tier 3 silently
                pass
            except Exception as e:
                # Unexpected error
                print(f"Error in semantic routing: {e}")
                # Fall through to tier 3

        # TIER 3: Simple fallback
        result = self._default_fallback(user_msg)
        result['execution_time_ms'] = int((time.time() - start_time) * 1000)
        result['method'] = 'fallback'
        self._log_decision(user_msg, result, log_decision)
        return result

    def _semantic_search(self, user_msg: str) -> Dict[str, Any]:
        """
        Perform semantic search in vector DB

        Returns routing decision based on nearest neighbors
        """
        # Query ChromaDB for similar examples
        results = self.collection.query(
            query_texts=[user_msg],
            n_results=MAX_SEARCH_RESULTS
        )

        # Check if we got results
        if not results['documents'] or not results['documents'][0]:
            return DEFAULT_ROUTE.copy()

        # Get top match
        top_document = results['documents'][0][0]
        top_distance = results['distances'][0][0]
        top_metadata = results['metadatas'][0][0]

        # Calculate similarity (ChromaDB uses distance, we want similarity)
        # Distance is L2 normalized, ranges 0-2, where 0 is identical
        similarity = 1 - (top_distance / 2)  # Convert to 0-1 scale

        # Check if similarity meets threshold
        if similarity >= SEMANTIC_SIMILARITY_THRESHOLD:
            # High confidence semantic match
            category = top_metadata.get('category', 'unknown')

            return {
                "use_rag": top_metadata['use_rag'],
                "use_logs": top_metadata['use_logs'],
                "use_web_search": top_metadata['use_web_search'],
                "reason": f"semantic:{category}",
                "confidence": similarity,
                "matched_example": top_document[:100],
                "category": category,
                "match_source": top_metadata.get('source', 'unknown')
            }

        elif similarity >= MIN_CONFIDENCE_THRESHOLD:
            # Medium confidence - use but log for review
            category = top_metadata.get('category', 'unknown')

            return {
                "use_rag": top_metadata['use_rag'],
                "use_logs": top_metadata['use_logs'],
                "use_web_search": top_metadata['use_web_search'],
                "reason": f"semantic_low_conf:{category}",
                "confidence": similarity,
                "matched_example": top_document[:100],
                "category": category,
                "match_source": top_metadata.get('source', 'unknown'),
                "warning": "Low confidence match - may need review"
            }

        else:
            # Below minimum threshold - fall through to keyword fallback (TIER 3)
            # Raise exception to trigger fallback in route() method
            raise ValueError(f"Low similarity ({similarity:.2f}) - falling back to keyword detection")

    def _default_fallback(self, user_msg: str) -> Dict[str, Any]:
        """
        Simple fallback routing when semantic routing unavailable
        Uses very basic keyword detection
        """
        t = user_msg.lower()

        # Very basic detection - minimal keywords
        # Note: Check plurals separately since "vulnerability" != "vulnerabilities" (y vs ies)
        threat_keywords = ["cve", "vulnerability", "vulnerabilities", "exploit", "exploits",
                          "threat", "threats", "malware", "breach", "attack"]
        if any(word in t for word in threat_keywords):
            return {
                "use_rag": False,
                "use_logs": False,
                "use_web_search": True,
                "reason": "fallback:threat-intelligence",
                "confidence": 0.5,
                "category": "threat_intelligence"
            }

        auth_keywords = ["login", "logins", "failed", "auth", "authentication",
                        "attempt", "attempts", "logout", "logouts", "password"]
        if any(word in t for word in auth_keywords):
            return {
                "use_rag": False,
                "use_logs": True,
                "use_web_search": False,
                "reason": "fallback:authentication-logs",
                "confidence": 0.5,
                "category": "authentication_logs"
            }

        policy_keywords = ["policy", "policies", "playbook", "playbooks", "procedure",
                          "procedures", "process", "processes", "guideline", "guidelines"]
        if any(word in t for word in policy_keywords):
            return {
                "use_rag": True,
                "use_logs": False,
                "use_web_search": False,
                "reason": "fallback:policy-guidance",
                "confidence": 0.5,
                "category": "policy_guidance"
            }

        # Default to RAG
        return DEFAULT_ROUTE.copy()

    def _log_decision(self, query: str, decision: Dict[str, Any], enabled: bool = True):
        """
        Log routing decision for analytics and continuous improvement

        Args:
            query: User's query text
            decision: Routing decision dict
            enabled: Whether logging is enabled
        """
        if not enabled:
            return

        try:
            # Import here to avoid circular dependency and handle missing module gracefully
            from .routing_logger import get_logger

            logger = get_logger()
            logger.log_decision(query, decision)

            # Log low-confidence warnings to console
            confidence = decision.get('confidence')
            if confidence and confidence < MIN_CONFIDENCE_THRESHOLD:
                print(f"⚠️  Low confidence routing ({confidence:.3f}): {query[:60]}...")
                print(f"   Method: {decision.get('method')} | Category: {decision.get('category')}")

        except Exception as e:
            # Silently fail - logging should not break routing
            pass

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the routing database
        """
        if not self.initialized or self.collection is None:
            return {
                "initialized": False,
                "total_examples": 0,
                "error": "Router not initialized"
            }

        try:
            count = self.collection.count()

            # Get category breakdown
            # Query all and count by category
            all_results = self.collection.get()
            category_counts = {}

            for metadata in all_results['metadatas']:
                cat = metadata.get('category', 'unknown')
                category_counts[cat] = category_counts.get(cat, 0) + 1

            return {
                "initialized": True,
                "total_examples": count,
                "category_breakdown": category_counts,
                "db_path": str(ROUTING_DB_PATH),
                "threshold": SEMANTIC_SIMILARITY_THRESHOLD,
                "categories": CATEGORIES
            }

        except Exception as e:
            return {
                "initialized": self.initialized,
                "error": str(e)
            }

    def get_analytics_stats(self) -> Dict[str, Any]:
        """
        Get analytics statistics from the routing logger

        Returns:
            Dict with routing decision analytics
        """
        try:
            from .routing_logger import get_logger

            logger = get_logger()
            return logger.get_stats()

        except Exception as e:
            return {
                "error": f"Could not get analytics stats: {e}"
            }


# Singleton instance
_router_instance: Optional[SemanticRouter] = None


def get_router() -> SemanticRouter:
    """
    Get or create the global semantic router instance
    """
    global _router_instance
    if _router_instance is None:
        _router_instance = SemanticRouter()
    return _router_instance


def reset_router():
    """
    Reset the router instance (useful for testing or reloading)
    """
    global _router_instance
    _router_instance = None
