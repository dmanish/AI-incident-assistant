"""
Routing Feedback and Learning System

This module implements a feedback loop to continuously improve routing accuracy:
1. Collect user feedback on routing decisions
2. Analyze feedback patterns
3. Automatically suggest new training examples
4. Update routing vector database
"""

import sqlite3
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path


class RoutingFeedback:
    """
    Manages user feedback on routing decisions to improve accuracy
    """

    def __init__(self, db_path: str = "data/routing/routing_metrics.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_feedback_table()

    def _init_feedback_table(self):
        """Create feedback table if it doesn't exist"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS routing_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    actual_route TEXT NOT NULL,  -- JSON: {use_rag, use_logs, use_web_search}
                    expected_route TEXT,          -- JSON: User's expected routing
                    feedback_type TEXT NOT NULL,  -- 'correct' | 'incorrect' | 'partial'
                    user_id TEXT,
                    session_id TEXT,
                    confidence_score REAL,
                    routing_method TEXT,          -- override/semantic/fallback
                    user_comment TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    processed INTEGER DEFAULT 0,  -- Whether incorporated into training
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_query
                ON routing_feedback(query)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_type
                ON routing_feedback(feedback_type)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_processed
                ON routing_feedback(processed)
            """)

            conn.commit()
        finally:
            conn.close()

    def record_feedback(
        self,
        query: str,
        actual_route: Dict[str, bool],
        feedback_type: str,
        expected_route: Optional[Dict[str, bool]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        confidence_score: Optional[float] = None,
        routing_method: Optional[str] = None,
        user_comment: Optional[str] = None
    ) -> int:
        """
        Record user feedback on a routing decision

        Args:
            query: The user's query
            actual_route: What the system chose
            feedback_type: 'correct' | 'incorrect' | 'partial'
            expected_route: What the user expected (if incorrect)
            user_id: User identifier
            session_id: Session identifier
            confidence_score: Original confidence score
            routing_method: Method used (override/semantic/fallback)
            user_comment: Optional user comment

        Returns:
            Feedback record ID
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute("""
                INSERT INTO routing_feedback (
                    query, actual_route, expected_route, feedback_type,
                    user_id, session_id, confidence_score, routing_method,
                    user_comment, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                query,
                json.dumps(actual_route),
                json.dumps(expected_route) if expected_route else None,
                feedback_type,
                user_id,
                session_id,
                confidence_score,
                routing_method,
                user_comment,
                datetime.now().isoformat()
            ])
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def analyze_feedback_patterns(
        self,
        days: int = 30,
        min_occurrences: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Analyze feedback to identify patterns of incorrect routing

        Args:
            days: Look back period in days
            min_occurrences: Minimum times a pattern must occur

        Returns:
            List of patterns with suggested improvements
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            since = (datetime.now() - timedelta(days=days)).isoformat()

            # Find queries with consistent incorrect routing
            cursor = conn.execute("""
                SELECT
                    query,
                    actual_route,
                    expected_route,
                    COUNT(*) as occurrences,
                    AVG(confidence_score) as avg_confidence,
                    GROUP_CONCAT(user_comment, ' | ') as comments
                FROM routing_feedback
                WHERE feedback_type = 'incorrect'
                  AND timestamp >= ?
                  AND expected_route IS NOT NULL
                  AND processed = 0
                GROUP BY query, actual_route, expected_route
                HAVING COUNT(*) >= ?
                ORDER BY occurrences DESC
            """, [since, min_occurrences])

            patterns = []
            for row in cursor.fetchall():
                query, actual_route, expected_route, occurrences, avg_conf, comments = row

                patterns.append({
                    "query": query,
                    "actual_route": json.loads(actual_route),
                    "expected_route": json.loads(expected_route),
                    "occurrences": occurrences,
                    "avg_confidence": avg_conf,
                    "user_comments": comments,
                    "suggested_action": "add_to_training",
                    "priority": "high" if occurrences >= 5 else "medium"
                })

            return patterns

        finally:
            conn.close()

    def generate_training_examples(
        self,
        patterns: Optional[List[Dict[str, Any]]] = None,
        auto_approve_threshold: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate new training examples from feedback patterns

        Args:
            patterns: Feedback patterns (if None, will analyze automatically)
            auto_approve_threshold: Auto-approve if occurrences >= threshold

        Returns:
            List of training examples ready for ingestion
        """
        if patterns is None:
            patterns = self.analyze_feedback_patterns()

        training_examples = []

        for pattern in patterns:
            query = pattern["query"]
            expected = pattern["expected_route"]
            occurrences = pattern["occurrences"]

            # Determine category based on expected route
            if expected.get("use_web_search"):
                category = "threat_intelligence"
            elif expected.get("use_logs"):
                category = "authentication_logs"
            elif expected.get("use_rag"):
                category = "policy_guidance"
            else:
                category = "unknown"

            training_example = {
                "query": query,
                "category": category,
                "use_rag": expected.get("use_rag", False),
                "use_logs": expected.get("use_logs", False),
                "use_web_search": expected.get("use_web_search", False),
                "source": "user_feedback",
                "occurrences": occurrences,
                "auto_approved": occurrences >= auto_approve_threshold,
                "priority": pattern.get("priority", "medium"),
                "user_comments": pattern.get("user_comments", "")
            }

            training_examples.append(training_example)

        return training_examples

    def export_training_examples(
        self,
        output_file: str = "data/routing/feedback_training_examples.json",
        auto_approve_only: bool = False
    ) -> int:
        """
        Export training examples to JSON file for review and ingestion

        Args:
            output_file: Output file path
            auto_approve_only: Only export auto-approved examples

        Returns:
            Number of examples exported
        """
        patterns = self.analyze_feedback_patterns()
        examples = self.generate_training_examples(patterns)

        if auto_approve_only:
            examples = [ex for ex in examples if ex.get("auto_approved")]

        # Save to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(examples, f, indent=2)

        print(f"✅ Exported {len(examples)} training examples to {output_file}")

        return len(examples)

    def mark_as_processed(self, query: str):
        """Mark feedback for a query as processed"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                UPDATE routing_feedback
                SET processed = 1
                WHERE query = ?
            """, [query])
            conn.commit()
        finally:
            conn.close()

    def get_feedback_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get statistics on routing feedback

        Args:
            days: Look back period

        Returns:
            Statistics dictionary
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            since = (datetime.now() - timedelta(days=days)).isoformat()

            # Overall feedback counts
            cursor = conn.execute("""
                SELECT
                    feedback_type,
                    COUNT(*) as count
                FROM routing_feedback
                WHERE timestamp >= ?
                GROUP BY feedback_type
            """, [since])

            feedback_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # Accuracy rate
            total = sum(feedback_counts.values())
            correct = feedback_counts.get('correct', 0)
            accuracy = (correct / total * 100) if total > 0 else 0

            # Unprocessed patterns
            cursor = conn.execute("""
                SELECT COUNT(DISTINCT query)
                FROM routing_feedback
                WHERE feedback_type = 'incorrect'
                  AND processed = 0
                  AND timestamp >= ?
            """, [since])

            unprocessed_patterns = cursor.fetchone()[0]

            return {
                "period_days": days,
                "total_feedback": total,
                "feedback_breakdown": feedback_counts,
                "accuracy_rate": round(accuracy, 2),
                "unprocessed_patterns": unprocessed_patterns,
                "can_generate_examples": unprocessed_patterns > 0
            }

        finally:
            conn.close()


# Singleton instance
_feedback_instance: Optional[RoutingFeedback] = None


def get_feedback_manager() -> RoutingFeedback:
    """Get or create the global feedback manager instance"""
    global _feedback_instance
    if _feedback_instance is None:
        _feedback_instance = RoutingFeedback()
    return _feedback_instance
