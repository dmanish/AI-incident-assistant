#!/usr/bin/env python3
"""
Phase 3: Analytics script for routing accuracy analysis

Analyzes routing decisions from SQLite database to:
- Identify low-confidence queries that need review
- Find patterns in misrouted queries
- Suggest new training examples for vector DB
- Generate reports on routing performance

Run periodically to improve routing accuracy
"""

import sqlite3
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys

# Add parent directory to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.agent.routing_config import PROJECT_ROOT as CONFIG_ROOT
from app.agent.routing_logger import ROUTING_METRICS_DB


def analyze_low_confidence_decisions(threshold: float = 0.75, days: int = 7) -> List[Dict]:
    """
    Find low-confidence routing decisions for review

    Args:
        threshold: Confidence threshold (default 0.75)
        days: Number of days to analyze

    Returns:
        List of low-confidence decisions with context
    """
    print(f"\n{'='*70}")
    print(f"ANALYZING LOW-CONFIDENCE DECISIONS (< {threshold})")
    print(f"{'='*70}\n")

    if not ROUTING_METRICS_DB.exists():
        print(f"⚠️  Metrics database not found: {ROUTING_METRICS_DB}")
        print("Run some queries first to populate routing metrics")
        return []

    conn = sqlite3.connect(str(ROUTING_METRICS_DB))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get low-confidence decisions from last N days
    since_date = (datetime.now() - timedelta(days=days)).isoformat()

    cursor.execute("""
        SELECT
            query, confidence, method, reason, category,
            matched_example, execution_time_ms, timestamp
        FROM routing_decisions
        WHERE confidence < ?
        AND timestamp >= ?
        AND method != 'override'
        ORDER BY confidence ASC
        LIMIT 100
    """, (threshold, since_date))

    results = cursor.fetchall()
    conn.close()

    if not results:
        print("✓ No low-confidence decisions found!")
        return []

    print(f"Found {len(results)} low-confidence decisions:\n")

    low_confidence_list = []
    for i, row in enumerate(results, 1):
        decision = {
            'query': row['query'],
            'confidence': row['confidence'],
            'method': row['method'],
            'reason': row['reason'],
            'category': row['category'],
            'matched_example': row['matched_example'],
            'timestamp': row['timestamp']
        }

        low_confidence_list.append(decision)

        # Print first 10 for review
        if i <= 10:
            print(f"{i}. Query: {decision['query'][:80]}")
            print(f"   Confidence: {decision['confidence']:.3f} | Method: {decision['method']} | Category: {decision['category']}")
            if decision['matched_example']:
                print(f"   Matched: {decision['matched_example'][:60]}...")
            print()

    if len(results) > 10:
        print(f"... and {len(results) - 10} more\n")

    return low_confidence_list


def analyze_method_performance(days: int = 7) -> Dict[str, Any]:
    """
    Analyze performance breakdown by routing method

    Args:
        days: Number of days to analyze

    Returns:
        Dict with method performance metrics
    """
    print(f"\n{'='*70}")
    print(f"METHOD PERFORMANCE ANALYSIS (Last {days} days)")
    print(f"{'='*70}\n")

    if not ROUTING_METRICS_DB.exists():
        print(f"⚠️  Metrics database not found")
        return {}

    conn = sqlite3.connect(str(ROUTING_METRICS_DB))
    cursor = conn.cursor()

    since_date = (datetime.now() - timedelta(days=days)).isoformat()

    # Get counts by method
    cursor.execute("""
        SELECT method, COUNT(*) as count,
               AVG(confidence) as avg_confidence,
               AVG(execution_time_ms) as avg_time_ms
        FROM routing_decisions
        WHERE timestamp >= ?
        GROUP BY method
        ORDER BY count DESC
    """, (since_date,))

    results = cursor.fetchall()
    conn.close()

    if not results:
        print("No routing data available\n")
        return {}

    total_decisions = sum(row[1] for row in results)

    print(f"Total Decisions: {total_decisions}\n")
    print(f"{'Method':<15} {'Count':<10} {'%':<8} {'Avg Conf':<12} {'Avg Time (ms)':<15}")
    print("-" * 70)

    method_stats = {}
    for method, count, avg_conf, avg_time in results:
        percentage = (count / total_decisions) * 100
        conf_str = f"{avg_conf:.3f}" if avg_conf else "N/A"
        time_str = f"{avg_time:.1f}" if avg_time else "N/A"

        print(f"{method:<15} {count:<10} {percentage:>6.1f}% {conf_str:<12} {time_str:<15}")

        method_stats[method] = {
            'count': count,
            'percentage': round(percentage, 2),
            'avg_confidence': round(avg_conf, 3) if avg_conf else None,
            'avg_time_ms': round(avg_time, 1) if avg_time else None
        }

    print()
    return method_stats


def analyze_category_distribution(days: int = 7) -> Dict[str, int]:
    """
    Analyze distribution of query categories

    Args:
        days: Number of days to analyze

    Returns:
        Dict of category -> count
    """
    print(f"\n{'='*70}")
    print(f"CATEGORY DISTRIBUTION (Last {days} days)")
    print(f"{'='*70}\n")

    if not ROUTING_METRICS_DB.exists():
        print(f"⚠️  Metrics database not found")
        return {}

    conn = sqlite3.connect(str(ROUTING_METRICS_DB))
    cursor = conn.cursor()

    since_date = (datetime.now() - timedelta(days=days)).isoformat()

    cursor.execute("""
        SELECT category, COUNT(*) as count
        FROM routing_decisions
        WHERE timestamp >= ?
        GROUP BY category
        ORDER BY count DESC
    """, (since_date,))

    results = cursor.fetchall()
    conn.close()

    if not results:
        print("No category data available\n")
        return {}

    total = sum(row[1] for row in results)

    print(f"Total Queries: {total}\n")
    print(f"{'Category':<30} {'Count':<10} {'%':<8}")
    print("-" * 50)

    category_counts = {}
    for category, count in results:
        percentage = (count / total) * 100
        print(f"{category:<30} {count:<10} {percentage:>6.1f}%")
        category_counts[category] = count

    print()
    return category_counts


def suggest_training_examples(threshold: float = 0.70, min_occurrences: int = 3) -> List[Dict]:
    """
    Suggest new training examples based on recurring low-confidence queries

    Args:
        threshold: Confidence threshold for low-confidence
        min_occurrences: Minimum times a query pattern must occur

    Returns:
        List of suggested training examples
    """
    print(f"\n{'='*70}")
    print(f"SUGGESTED TRAINING EXAMPLES")
    print(f"{'='*70}\n")

    if not ROUTING_METRICS_DB.exists():
        print(f"⚠️  Metrics database not found")
        return []

    conn = sqlite3.connect(str(ROUTING_METRICS_DB))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Find low-confidence queries
    cursor.execute("""
        SELECT query, category,
               AVG(confidence) as avg_confidence,
               COUNT(*) as occurrences,
               MAX(use_rag) as use_rag,
               MAX(use_logs) as use_logs,
               MAX(use_web_search) as use_web_search
        FROM routing_decisions
        WHERE confidence < ? AND method != 'override'
        GROUP BY LOWER(query)
        HAVING COUNT(*) >= ?
        ORDER BY occurrences DESC, avg_confidence ASC
        LIMIT 20
    """, (threshold, min_occurrences))

    results = cursor.fetchall()
    conn.close()

    if not results:
        print("✓ No recurring low-confidence patterns found!")
        print("Your routing is performing well.\n")
        return []

    print(f"Found {len(results)} query patterns that could benefit from training examples:\n")

    suggestions = []
    for i, row in enumerate(results, 1):
        suggestion = {
            'id': f'suggested_{i:03d}',
            'query': row['query'],
            'category': row['category'],
            'use_rag': bool(row['use_rag']),
            'use_logs': bool(row['use_logs']),
            'use_web_search': bool(row['use_web_search']),
            'source': 'analytics_suggestion',
            'avg_confidence': round(row['avg_confidence'], 3),
            'occurrences': row['occurrences'],
            'notes': f'Recurring query with low confidence (avg: {row["avg_confidence"]:.3f})'
        }

        suggestions.append(suggestion)

        print(f"{i}. Query: {suggestion['query'][:70]}")
        print(f"   Category: {suggestion['category']} | Occurrences: {suggestion['occurrences']} | Avg Confidence: {suggestion['avg_confidence']:.3f}")
        print(f"   Suggested Route: rag={suggestion['use_rag']}, logs={suggestion['use_logs']}, web={suggestion['use_web_search']}")
        print()

    # Save suggestions to file for manual review
    suggestions_file = PROJECT_ROOT / "data" / "routing" / "suggested_examples.json"
    suggestions_file.parent.mkdir(parents=True, exist_ok=True)

    with open(suggestions_file, 'w') as f:
        json.dump(suggestions, f, indent=2)

    print(f"✓ Saved suggestions to: {suggestions_file}\n")
    print("Review these suggestions and add valid ones to seed_examples.json")
    print("Then re-run ingest_routing_examples.py to update the vector DB\n")

    return suggestions


def generate_report(days: int = 7) -> Dict[str, Any]:
    """
    Generate comprehensive routing performance report

    Args:
        days: Number of days to analyze

    Returns:
        Dict with full report data
    """
    print(f"\n{'='*70}")
    print(f"ROUTING PERFORMANCE REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    report = {
        'generated_at': datetime.now().isoformat(),
        'analysis_period_days': days
    }

    # Overall stats
    if ROUTING_METRICS_DB.exists():
        conn = sqlite3.connect(str(ROUTING_METRICS_DB))
        cursor = conn.cursor()

        since_date = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT
                COUNT(*) as total,
                AVG(confidence) as avg_conf,
                MIN(confidence) as min_conf,
                MAX(confidence) as max_conf,
                AVG(execution_time_ms) as avg_time
            FROM routing_decisions
            WHERE timestamp >= ?
        """, (since_date,))

        row = cursor.fetchone()
        conn.close()

        report['overall'] = {
            'total_decisions': row[0],
            'avg_confidence': round(row[1], 3) if row[1] else None,
            'min_confidence': round(row[2], 3) if row[2] else None,
            'max_confidence': round(row[3], 3) if row[3] else None,
            'avg_execution_time_ms': round(row[4], 2) if row[4] else None
        }

        print(f"Overall Statistics:")
        print(f"  Total Decisions: {report['overall']['total_decisions']}")
        print(f"  Avg Confidence: {report['overall']['avg_confidence']}")
        print(f"  Min Confidence: {report['overall']['min_confidence']}")
        print(f"  Max Confidence: {report['overall']['max_confidence']}")
        print(f"  Avg Execution Time: {report['overall']['avg_execution_time_ms']} ms")
    else:
        print("⚠️  No metrics database found")
        return report

    # Method performance
    report['method_performance'] = analyze_method_performance(days)

    # Category distribution
    report['category_distribution'] = analyze_category_distribution(days)

    # Low confidence decisions
    report['low_confidence_queries'] = analyze_low_confidence_decisions(threshold=0.75, days=days)

    # Suggestions
    report['suggested_training_examples'] = suggest_training_examples(threshold=0.70, min_occurrences=2)

    # Save report
    report_file = PROJECT_ROOT / "data" / "routing" / f"routing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)

    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n{'='*70}")
    print(f"✓ Full report saved to: {report_file}")
    print(f"{'='*70}\n")

    return report


def main():
    """Main analytics workflow"""
    print("\n" + "="*70)
    print("SEMANTIC ROUTING ACCURACY ANALYSIS")
    print("="*70)

    # Check if database exists
    if not ROUTING_METRICS_DB.exists():
        print(f"\n⚠️  Metrics database not found: {ROUTING_METRICS_DB}")
        print("\nThe routing logger will create this database automatically")
        print("as queries are processed. Run some queries first, then re-run")
        print("this script to see analytics.\n")
        return 1

    # Generate comprehensive report (7 days by default)
    generate_report(days=7)

    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    print("""
1. Review low-confidence queries and add them to seed_examples.json if valid
2. Check suggested training examples in data/routing/suggested_examples.json
3. Update override rules in config/routing_rules.yaml for critical patterns
4. Re-run scripts/ingest_routing_examples.py to update vector DB
5. Monitor method performance - aim for >80% semantic routing
6. Target avg execution time < 70ms for good performance
""")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
