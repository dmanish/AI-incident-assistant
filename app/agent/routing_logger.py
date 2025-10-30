# app/agent/routing_logger.py
"""
Phase 3: Continuous improvement logging for semantic routing

Logs routing decisions to SQLite for analysis and improvement:
- Tracks confidence scores and matched examples
- Identifies low-confidence decisions for review
- Enables analytics to improve routing accuracy over time
"""

import sqlite3
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from .routing_config import PROJECT_ROOT

# Database path
ROUTING_METRICS_DB = PROJECT_ROOT / "data" / "routing" / "routing_metrics.db"


class RoutingLogger:
    """
    Logs routing decisions to SQLite database for analytics
    Enables continuous improvement of semantic routing
    """

    def __init__(self):
        """Initialize the routing logger and ensure database exists"""
        self.db_path = ROUTING_METRICS_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def _initialize_database(self):
        """Create routing metrics database if it doesn't exist"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Create routing_decisions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS routing_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                query TEXT NOT NULL,
                method TEXT NOT NULL,
                category TEXT,
                use_rag INTEGER NOT NULL,
                use_logs INTEGER NOT NULL,
                use_web_search INTEGER NOT NULL,
                confidence REAL,
                reason TEXT,
                matched_example TEXT,
                matched_rule TEXT,
                match_source TEXT,
                execution_time_ms INTEGER,
                user_feedback TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON routing_decisions(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_method
            ON routing_decisions(method)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_confidence
            ON routing_decisions(confidence)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_category
            ON routing_decisions(category)
        """)

        conn.commit()
        conn.close()

    def log_decision(
        self,
        query: str,
        decision: Dict[str, Any],
        user_feedback: Optional[str] = None,
        notes: Optional[str] = None
    ):
        """
        Log a routing decision to the database

        Args:
            query: User's query text
            decision: Routing decision dict from semantic_router
            user_feedback: Optional user feedback (correct/incorrect)
            notes: Optional notes about this decision
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Extract fields from decision
            timestamp = datetime.utcnow().isoformat()
            method = decision.get('method', 'unknown')
            category = decision.get('category', 'unknown')
            use_rag = int(decision.get('use_rag', False))
            use_logs = int(decision.get('use_logs', False))
            use_web_search = int(decision.get('use_web_search', False))
            confidence = decision.get('confidence')
            reason = decision.get('reason', '')
            matched_example = decision.get('matched_example', '')[:200]  # Limit length
            matched_rule = decision.get('matched_rule', '')
            match_source = decision.get('match_source', '')
            execution_time_ms = decision.get('execution_time_ms')

            cursor.execute("""
                INSERT INTO routing_decisions (
                    timestamp, query, method, category,
                    use_rag, use_logs, use_web_search,
                    confidence, reason, matched_example, matched_rule,
                    match_source, execution_time_ms, user_feedback, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, query[:500], method, category,
                use_rag, use_logs, use_web_search,
                confidence, reason, matched_example, matched_rule,
                match_source, execution_time_ms, user_feedback, notes
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Warning: Failed to log routing decision: {e}")

    def get_low_confidence_queries(self, threshold: float = 0.75, limit: int = 50) -> list:
        """
        Get queries with low confidence scores for review

        Args:
            threshold: Confidence threshold (default 0.75)
            limit: Maximum number of results

        Returns:
            List of (query, confidence, method, reason) tuples
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT query, confidence, method, reason, category, timestamp
                FROM routing_decisions
                WHERE confidence < ? AND method != 'override'
                ORDER BY confidence ASC, timestamp DESC
                LIMIT ?
            """, (threshold, limit))

            results = cursor.fetchall()
            conn.close()
            return results

        except Exception as e:
            print(f"Error getting low confidence queries: {e}")
            return []

    def get_method_breakdown(self, days: int = 7) -> Dict[str, int]:
        """
        Get breakdown of routing methods used in last N days

        Args:
            days: Number of days to analyze

        Returns:
            Dict of method -> count
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT method, COUNT(*) as count
                FROM routing_decisions
                WHERE timestamp >= datetime('now', '-' || ? || ' days')
                GROUP BY method
                ORDER BY count DESC
            """, (days,))

            results = cursor.fetchall()
            conn.close()

            return {method: count for method, count in results}

        except Exception as e:
            print(f"Error getting method breakdown: {e}")
            return {}

    def get_category_breakdown(self, days: int = 7) -> Dict[str, int]:
        """
        Get breakdown of categories in last N days

        Args:
            days: Number of days to analyze

        Returns:
            Dict of category -> count
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM routing_decisions
                WHERE timestamp >= datetime('now', '-' || ? || ' days')
                GROUP BY category
                ORDER BY count DESC
            """, (days,))

            results = cursor.fetchall()
            conn.close()

            return {category: count for category, count in results}

        except Exception as e:
            print(f"Error getting category breakdown: {e}")
            return {}

    def get_avg_confidence_by_method(self) -> Dict[str, float]:
        """
        Get average confidence score by routing method

        Returns:
            Dict of method -> avg_confidence
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT method, AVG(confidence) as avg_conf
                FROM routing_decisions
                WHERE confidence IS NOT NULL
                GROUP BY method
            """)

            results = cursor.fetchall()
            conn.close()

            return {method: round(conf, 3) for method, conf in results}

        except Exception as e:
            print(f"Error getting avg confidence: {e}")
            return {}

    def get_stats(self) -> Dict[str, Any]:
        """
        Get overall statistics about routing decisions

        Returns:
            Dict with statistics
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Total decisions
            cursor.execute("SELECT COUNT(*) FROM routing_decisions")
            total = cursor.fetchone()[0]

            # Decisions by method
            cursor.execute("""
                SELECT method, COUNT(*) FROM routing_decisions GROUP BY method
            """)
            method_counts = dict(cursor.fetchall())

            # Average confidence
            cursor.execute("""
                SELECT AVG(confidence) FROM routing_decisions WHERE confidence IS NOT NULL
            """)
            avg_confidence = cursor.fetchone()[0]

            # Low confidence count
            cursor.execute("""
                SELECT COUNT(*) FROM routing_decisions WHERE confidence < 0.75
            """)
            low_confidence_count = cursor.fetchone()[0]

            # Average execution time
            cursor.execute("""
                SELECT AVG(execution_time_ms) FROM routing_decisions
                WHERE execution_time_ms IS NOT NULL
            """)
            avg_time = cursor.fetchone()[0]

            conn.close()

            return {
                "total_decisions": total,
                "method_breakdown": method_counts,
                "avg_confidence": round(avg_confidence, 3) if avg_confidence else None,
                "low_confidence_count": low_confidence_count,
                "avg_execution_time_ms": round(avg_time, 2) if avg_time else None,
                "database_path": str(self.db_path)
            }

        except Exception as e:
            return {"error": str(e)}


# Singleton instance
_logger_instance: Optional[RoutingLogger] = None


def get_logger() -> RoutingLogger:
    """Get or create the global routing logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = RoutingLogger()
    return _logger_instance


def reset_logger():
    """Reset the logger instance (useful for testing)"""
    global _logger_instance
    _logger_instance = None
