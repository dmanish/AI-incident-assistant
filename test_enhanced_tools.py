#!/usr/bin/env python3
"""
Test script for enhanced tool system
Tests all new functionality: date ranges, aggregations, web search, etc.
"""

import sys
import os
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agent.tools_enhanced import TOOL_DEFINITIONS, format_tool_result
from app.agent.executors_enhanced import EnhancedToolExecutors
from datetime import datetime, timedelta
import pandas as pd


def mock_retrieve_chunks(query: str, role: str, top_k: int = 5):
    """Mock RAG retrieval"""
    return [
        {
            "text": f"Mock policy content for query: {query}",
            "metadata": {"source_path": "mock_policy.pdf", "doc_type": "policy"}
        }
    ]


def mock_query_logs(
    date_start: str,
    date_end: str = None,
    result_filter: str = "failed",
    username: str = None,
    ip_address: str = None,
    limit: int = 200
):
    """Mock log query that returns sample data"""
    # Create sample authentication log data
    data = []

    start_date = datetime.fromisoformat(date_start)
    end_date = datetime.fromisoformat(date_end) if date_end else start_date

    # Generate sample logs
    users = ["alice", "bob", "charlie", "dave"]
    ips = ["192.168.1.100", "192.168.1.101", "10.0.0.5", "172.16.0.10"]
    results = {
        "failed": ["failed"],
        "successful": ["successful"],
        "all": ["failed", "successful"]
    }

    current_date = start_date
    while current_date <= end_date:
        for hour in range(0, 24, 2):  # Every 2 hours
            for user in users:
                for ip in ips[:2]:  # Use first 2 IPs
                    # Filter by username if specified
                    if username and user != username.lower():
                        continue
                    # Filter by IP if specified
                    if ip_address and ip != ip_address:
                        continue

                    # Add some failed and successful attempts
                    for result in results.get(result_filter, ["failed"]):
                        data.append({
                            "timestamp": current_date.replace(hour=hour).isoformat(),
                            "user": user,
                            "action": "login",
                            "result": result,
                            "ip": ip
                        })
        current_date += timedelta(days=1)

    df = pd.DataFrame(data)
    return df.head(limit) if len(df) > limit else df


def mock_role_allows_tool(role: str, tool: str) -> bool:
    """Mock RBAC check"""
    if role in ["security", "engineering"]:
        return True
    return False


def mock_role_allows_doc(role: str, doc_type: str) -> bool:
    """Mock doc RBAC check"""
    return True


def print_section(title: str):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_tool_definitions():
    """Test that tool definitions are properly structured"""
    print_section("TEST 1: Tool Definitions")

    print(f"\n✓ Found {len(TOOL_DEFINITIONS)} tool definitions:")
    for tool in TOOL_DEFINITIONS:
        name = tool["function"]["name"]
        desc = tool["function"]["description"][:80]
        print(f"  - {name}: {desc}...")

    # Verify required tools exist
    tool_names = [t["function"]["name"] for t in TOOL_DEFINITIONS]
    required_tools = [
        "search_authentication_logs",
        "search_knowledge_base",
        "search_threat_intelligence"
    ]

    for req_tool in required_tools:
        if req_tool in tool_names:
            print(f"  ✓ {req_tool} defined")
        else:
            print(f"  ✗ {req_tool} MISSING")


def test_date_parsing():
    """Test relative date parsing"""
    print_section("TEST 2: Date Parsing")

    executors = EnhancedToolExecutors(
        retrieve_chunks_fn=mock_retrieve_chunks,
        query_logs_fn=mock_query_logs,
        role_allows_tool_fn=mock_role_allows_tool,
        role_allows_doc_fn=mock_role_allows_doc
    )

    test_cases = [
        "today",
        "yesterday",
        "last_7_days",
        "last_30_days",
        "this_week",
        "this_month",
        "2025-10-28"
    ]

    print("\nRelative date parsing:")
    for test_date in test_cases:
        result = executors._parse_relative_date(test_date)
        print(f"  '{test_date}' → {result}")


def test_authentication_log_search():
    """Test enhanced authentication log search"""
    print_section("TEST 3: Authentication Log Search")

    executors = EnhancedToolExecutors(
        retrieve_chunks_fn=mock_retrieve_chunks,
        query_logs_fn=mock_query_logs,
        role_allows_tool_fn=mock_role_allows_tool,
        role_allows_doc_fn=mock_role_allows_doc
    )

    test_cases = [
        {
            "name": "Simple failed login query",
            "args": {
                "date_start": "today",
                "result_filter": "failed"
            }
        },
        {
            "name": "Date range with all auth events",
            "args": {
                "date_start": "last_7_days",
                "date_end": "today",
                "result_filter": "all"
            }
        },
        {
            "name": "Filter by username",
            "args": {
                "date_start": "today",
                "username": "alice",
                "result_filter": "failed"
            }
        },
        {
            "name": "Aggregation by user",
            "args": {
                "date_start": "last_7_days",
                "result_filter": "failed",
                "aggregate_by": "user"
            }
        },
        {
            "name": "Aggregation by IP",
            "args": {
                "date_start": "last_7_days",
                "result_filter": "all",
                "aggregate_by": "ip"
            }
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {test['name']} ---")
        result = executors.execute_search_authentication_logs(
            arguments=test["args"],
            role="security"
        )
        print(f"  Total records: {result['count']}")
        print(f"  Date range: {result['date_range']['start']} to {result['date_range']['end']}")
        print(f"  Filters: {result['filters']}")
        if result.get('aggregation'):
            print(f"  Aggregation: {len(result['aggregation'])} groups")
            for agg in result['aggregation'][:3]:
                print(f"    - {agg['group_key']}: {agg['count']}")
        if result.get('sample'):
            print(f"  Sample records: {len(result['sample'])}")


def test_formatted_output():
    """Test tool result formatting"""
    print_section("TEST 4: Tool Result Formatting")

    # Create sample result
    sample_result = {
        "count": 150,
        "date_range": {"start": "2025-10-21", "end": "2025-10-28"},
        "filters": {
            "result_filter": "failed",
            "username": "alice",
            "ip_address": None
        },
        "aggregation": [
            {"group_key": "192.168.1.100", "count": 45},
            {"group_key": "192.168.1.101", "count": 30}
        ],
        "sample": [
            {
                "timestamp": "2025-10-28T10:30:00",
                "user": "alice",
                "ip": "192.168.1.100",
                "result": "failed"
            }
        ]
    }

    formatted = format_tool_result("search_authentication_logs", sample_result, success=True)
    print("\nFormatted output for LLM:")
    print(formatted)


def test_threat_intelligence():
    """Test web-based threat intelligence search"""
    print_section("TEST 5: Threat Intelligence Search")

    executors = EnhancedToolExecutors(
        retrieve_chunks_fn=mock_retrieve_chunks,
        query_logs_fn=mock_query_logs,
        role_allows_tool_fn=mock_role_allows_tool,
        role_allows_doc_fn=mock_role_allows_doc
    )

    test_cases = [
        {
            "name": "General threat intel",
            "args": {
                "query": "latest ransomware threats 2024",
                "search_type": "general"
            }
        },
        {
            "name": "CVE lookup",
            "args": {
                "query": "CVE-2024-1234",
                "search_type": "cve"
            }
        },
        {
            "name": "IP reputation",
            "args": {
                "query": "1.2.3.4",
                "search_type": "ip_reputation"
            }
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {test['name']} ---")
        print(f"  Query: {test['args']['query']}")
        print(f"  Type: {test['args']['search_type']}")

        result = executors.execute_search_threat_intelligence(
            arguments=test["args"],
            role="security"
        )

        print(f"  Results found: {len(result.get('results', []))}")
        if result.get('results'):
            for j, item in enumerate(result['results'][:2], 1):
                print(f"    {j}. {item.get('title', 'N/A')[:60]}")
        if result.get('error'):
            print(f"  Error: {result['error']}")


def test_rbac():
    """Test RBAC enforcement"""
    print_section("TEST 7: RBAC Enforcement")

    executors = EnhancedToolExecutors(
        retrieve_chunks_fn=mock_retrieve_chunks,
        query_logs_fn=mock_query_logs,
        role_allows_tool_fn=mock_role_allows_tool,
        role_allows_doc_fn=mock_role_allows_doc
    )

    print("\nTesting RBAC for log queries...")

    # Authorized role
    try:
        result = executors.execute_search_authentication_logs(
            arguments={"date_start": "today"},
            role="security"
        )
        print(f"  ✓ Security role: ALLOWED (count={result['count']})")
    except PermissionError:
        print(f"  ✗ Security role: DENIED (unexpected)")

    # Unauthorized role
    try:
        result = executors.execute_search_authentication_logs(
            arguments={"date_start": "today"},
            role="sales"
        )
        print(f"  ✗ Sales role: ALLOWED (unexpected, count={result['count']})")
    except PermissionError as e:
        print(f"  ✓ Sales role: DENIED (expected)")


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  ENHANCED TOOL SYSTEM TEST SUITE")
    print("=" * 70)

    tests = [
        ("Tool Definitions", test_tool_definitions),
        ("Date Parsing", test_date_parsing),
        ("Authentication Log Search", test_authentication_log_search),
        ("Formatted Output", test_formatted_output),
        ("Threat Intelligence", test_threat_intelligence),
        ("RBAC Enforcement", test_rbac)
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n✗ TEST FAILED: {name}")
            print(f"  Error: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1

    # Summary
    print("\n" + "=" * 70)
    print(f"  TEST SUMMARY")
    print("=" * 70)
    print(f"  Total tests: {passed + failed}")
    print(f"  ✓ Passed: {passed}")
    print(f"  ✗ Failed: {failed}")
    print("=" * 70 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
