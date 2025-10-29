# app/agent/semantic_router.py
"""
Semantic routing using vector similarity instead of keyword matching
Routes user queries to appropriate tools based on semantic meaning
"""

from typing import Dict, Any, Optional
import os


class SemanticRouter:
    """
    Routes queries using semantic similarity with ChromaDB
    Falls back to config-based rules when needed
    """

    def __init__(self):
        """
        Initialize the semantic router
        Will be populated with vector DB and config in Phase 1
        """
        # Placeholder - will be implemented in Phase 1
        self.initialized = False
        self.fallback_enabled = True

    def route(self, user_msg: str) -> Dict[str, Any]:
        """
        Route a user query to appropriate tools

        Args:
            user_msg: User's query text

        Returns:
            Dict with:
                - use_rag: bool
                - use_logs: bool
                - use_web_search: bool
                - reason: str (e.g., "semantic:threat_intelligence")
                - confidence: float (0-1, optional)
                - matched_example: str (optional)
        """
        # Phase 0-1 implementation will replace this
        # For now, use simple fallback to maintain functionality
        return self._default_fallback(user_msg)

    def _default_fallback(self, user_msg: str) -> Dict[str, Any]:
        """
        Simple fallback routing when semantic routing not yet initialized
        This is a minimal fallback - the real logic will be vector-based
        """
        t = user_msg.lower()

        # Very basic detection - this will be replaced by semantic routing
        if any(word in t for word in ["cve", "vulnerability", "exploit", "threat"]):
            return {
                "use_rag": False,
                "use_logs": False,
                "use_web_search": True,
                "reason": "fallback:threat-intelligence",
                "confidence": 0.5
            }

        if any(word in t for word in ["login", "failed", "auth", "attempt"]):
            return {
                "use_rag": False,
                "use_logs": True,
                "use_web_search": False,
                "reason": "fallback:authentication-logs",
                "confidence": 0.5
            }

        if any(word in t for word in ["policy", "playbook", "procedure", "process"]):
            return {
                "use_rag": True,
                "use_logs": False,
                "use_web_search": False,
                "reason": "fallback:policy-guidance",
                "confidence": 0.5
            }

        # Default to RAG
        return {
            "use_rag": True,
            "use_logs": False,
            "use_web_search": False,
            "reason": "fallback:default-rag",
            "confidence": 0.3
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
