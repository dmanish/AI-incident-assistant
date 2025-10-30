# app/agent/rule_matcher.py
"""
Rule matcher for override-based routing
Evaluates YAML config rules before semantic search

Phase 2 Implementation: Config-based overrides
"""

import re
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
from .routing_config import CONFIG_FILE


class RuleMatcher:
    """
    Evaluates override rules from routing_rules.yaml
    Rules are checked in priority order (highest first)
    """

    def __init__(self):
        """Initialize rule matcher with config file"""
        self.rules = []
        self.config = {}
        self.initialized = False

        try:
            self._load_config()
        except Exception as e:
            print(f"Warning: Could not load routing rules: {e}")
            print("Override rules will be disabled")

    def _load_config(self):
        """Load routing rules from YAML config"""
        if not CONFIG_FILE.exists():
            print(f"Warning: Config file not found: {CONFIG_FILE}")
            return

        with open(CONFIG_FILE, 'r') as f:
            self.config = yaml.safe_load(f)

        # Extract and sort override rules by priority
        overrides = self.config.get('overrides', [])
        self.rules = sorted(overrides, key=lambda r: r.get('priority', 0), reverse=True)

        self.initialized = True
        print(f"✓ Loaded {len(self.rules)} override rules from config")

    def check_overrides(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Check if query matches any override rules

        Args:
            query: User query text

        Returns:
            Routing decision if match found, None otherwise
        """
        if not self.initialized or not self.rules:
            return None

        # Check each rule in priority order
        for rule in self.rules:
            if self._matches_rule(query, rule):
                return self._build_response(rule)

        return None

    def _matches_rule(self, query: str, rule: Dict) -> bool:
        """Check if query matches a specific rule"""
        rule_type = rule.get('type', '').lower()

        if rule_type == 'regex':
            return self._matches_regex(query, rule)
        elif rule_type == 'keyword':
            return self._matches_keywords(query, rule)
        else:
            return False

    def _matches_regex(self, query: str, rule: Dict) -> bool:
        """Check if query matches regex pattern(s)"""
        patterns = rule.get('patterns', [])

        # Single pattern
        if 'pattern' in rule:
            patterns.append(rule['pattern'])

        # Check all patterns (OR logic)
        for pattern in patterns:
            try:
                if re.search(pattern, query, re.IGNORECASE):
                    return True
            except re.error:
                print(f"Warning: Invalid regex pattern: {pattern}")
                continue

        return False

    def _matches_keywords(self, query: str, rule: Dict) -> bool:
        """Check if query matches keyword list"""
        keywords = rule.get('keywords', [])
        require_all = rule.get('require_all', False)

        query_lower = query.lower()

        if require_all:
            # ALL keywords must be present (AND logic)
            return all(kw.lower() in query_lower for kw in keywords)
        else:
            # ANY keyword must be present (OR logic)
            return any(kw.lower() in query_lower for kw in keywords)

    def _build_response(self, rule: Dict) -> Dict[str, Any]:
        """Build routing response from matched rule"""
        route = rule.get('route', {})

        return {
            "use_rag": route.get('use_rag', False),
            "use_logs": route.get('use_logs', False),
            "use_web_search": route.get('use_web_search', False),
            "reason": rule.get('reason', 'override:unknown'),
            "confidence": 1.0,  # Overrides are absolute
            "category": rule.get('category', 'unknown'),
            "matched_rule": rule.get('name', 'unknown'),
            "rule_description": rule.get('description', ''),
            "method": "override"
        }

    def get_rule_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded rules"""
        if not self.initialized:
            return {
                "initialized": False,
                "total_rules": 0,
                "error": "Rules not loaded"
            }

        # Count by category
        category_counts = {}
        for rule in self.rules:
            cat = rule.get('category', 'unknown')
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Count by type
        type_counts = {}
        for rule in self.rules:
            rule_type = rule.get('type', 'unknown')
            type_counts[rule_type] = type_counts.get(rule_type, 0) + 1

        return {
            "initialized": True,
            "total_rules": len(self.rules),
            "config_file": str(CONFIG_FILE),
            "category_breakdown": category_counts,
            "type_breakdown": type_counts,
            "highest_priority": self.rules[0].get('priority', 0) if self.rules else 0,
            "lowest_priority": self.rules[-1].get('priority', 0) if self.rules else 0
        }


# Singleton instance
_matcher_instance: Optional[RuleMatcher] = None


def get_matcher() -> RuleMatcher:
    """Get or create the global rule matcher instance"""
    global _matcher_instance
    if _matcher_instance is None:
        _matcher_instance = RuleMatcher()
    return _matcher_instance


def reset_matcher():
    """Reset the matcher instance (useful for testing or reloading)"""
    global _matcher_instance
    _matcher_instance = None
