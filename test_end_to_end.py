#!/usr/bin/env python3
"""
End-to-end test: Verify complete flow from routing to web search results
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_complete_flow():
    """Test the complete flow: routing → web search → formatted results"""
    from app.agent.agent import decide_tools
    from app.utils.web_search import search_threat_intelligence, format_search_results

    print("=" * 70)
    print("END-TO-END TEST: Complete CVE Query Flow")
    print("=" * 70)

    # User's original failing query
    user_query = "any vulnerabilities reported this year on glibc"

    print(f"\nUser Query: \"{user_query}\"")
    print("\n" + "-" * 70)
    print("STEP 1: Agent Routing")
    print("-" * 70)

    # Step 1: Route the query
    routing_decision = decide_tools(user_query)

    print(f"Routing Decision:")
    print(f"  use_rag: {routing_decision.get('use_rag')}")
    print(f"  use_logs: {routing_decision.get('use_logs')}")
    print(f"  use_web_search: {routing_decision.get('use_web_search')}")
    print(f"  reason: {routing_decision.get('reason')}")

    if not routing_decision.get('use_web_search'):
        print("\n✗ FAIL: Query not routed to web search!")
        return 1

    print("\n✓ PASS: Query correctly routed to web search")

    print("\n" + "-" * 70)
    print("STEP 2: Web Search Execution")
    print("-" * 70)

    # Step 2: Execute web search
    search_response = search_threat_intelligence(
        query=user_query,
        search_type="cve",
        max_results=3
    )

    result_count = search_response.get('result_count', 0)
    source = search_response.get('source', 'unknown')

    print(f"Search Source: {source}")
    print(f"Results Found: {result_count}")

    if result_count == 0:
        print("\n✗ FAIL: No results returned from web search!")
        return 1

    print("\n✓ PASS: Web search returned results")

    # Show results
    results = search_response.get('results', [])
    print("\nResults:")
    for i, result in enumerate(results, 1):
        print(f"\n  {i}. {result.get('title', 'No title')}")
        snippet = result.get('snippet', '')
        print(f"     {snippet[:100]}...")
        print(f"     URL: {result.get('url', 'N/A')}")

    print("\n" + "-" * 70)
    print("STEP 3: Format Results for LLM")
    print("-" * 70)

    # Step 3: Format for LLM
    formatted_results = format_search_results(search_response)

    print("Formatted context length:", len(formatted_results), "characters")
    print("\nFormatted output preview:")
    print(formatted_results[:400] + "...")

    if len(formatted_results) < 50:
        print("\n✗ FAIL: Formatted results too short!")
        return 1

    print("\n✓ PASS: Results formatted for LLM synthesis")

    print("\n" + "=" * 70)
    print("END-TO-END TEST RESULT")
    print("=" * 70)

    print("\n✓✓✓ COMPLETE FLOW WORKING ✓✓✓")
    print("\nSummary:")
    print(f"  ✅ Routing: Web Search (correct)")
    print(f"  ✅ Search: {result_count} results from {source}")
    print(f"  ✅ Formatting: {len(formatted_results)} chars ready for LLM")
    print("\nThe user's query will now receive actual CVE data instead of blank results!")

    return 0


def test_different_query_types():
    """Test routing for different query types"""
    from app.agent.agent import decide_tools

    print("\n" + "=" * 70)
    print("BONUS TEST: Verify All Query Types Route Correctly")
    print("=" * 70)

    test_queries = [
        ("is there a CVE on TLS", "web_search", "CVE query"),
        ("show failed logins today", "logs", "Log query"),
        ("what is our password policy", "rag", "Policy query"),
        ("latest ransomware threats", "web_search", "Threat intel query")
    ]

    passed = 0
    failed = 0

    for query, expected_tool, description in test_queries:
        routing = decide_tools(query)

        if expected_tool == "web_search":
            correct = routing.get('use_web_search') == True
        elif expected_tool == "logs":
            correct = routing.get('use_logs') == True
        elif expected_tool == "rag":
            correct = routing.get('use_rag') == True
        else:
            correct = False

        status = "✓" if correct else "✗"
        result = "PASS" if correct else "FAIL"

        print(f"\n{status} {result}: {description}")
        print(f"  Query: \"{query}\"")
        print(f"  Expected: {expected_tool}, Got: ", end="")

        if routing.get('use_web_search'):
            print("web_search")
        elif routing.get('use_logs'):
            print("logs")
        elif routing.get('use_rag'):
            print("rag")

        if correct:
            passed += 1
        else:
            failed += 1

    print("\n" + "-" * 70)
    print(f"Routing Tests: {passed} passed, {failed} failed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    # Run main test
    result1 = test_complete_flow()

    # Run routing verification
    result2 = test_different_query_types()

    # Exit with failure if any test failed
    sys.exit(max(result1, result2))
