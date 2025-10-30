#!/usr/bin/env python3
"""
Test web search routing in heuristic agent
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_routing():
    """Test that CVE queries route to web search"""
    from app.agent.agent import decide_tools

    print("=" * 70)
    print("Testing Web Search Routing")
    print("=" * 70)

    test_cases = [
        {
            "query": "what vulnerability was reported this month on TCP",
            "expected": "web_search",
            "should_use": {"use_rag": False, "use_logs": False, "use_web_search": True}
        },
        {
            "query": "any CVE reported this year on TCP",
            "expected": "web_search",
            "should_use": {"use_rag": False, "use_logs": False, "use_web_search": True}
        },
        {
            "query": "is there a CVE on TLS",
            "expected": "web_search",
            "should_use": {"use_rag": False, "use_logs": False, "use_web_search": True}
        },
        {
            "query": "show failed logins today",
            "expected": "logs",
            "should_use": {"use_rag": False, "use_logs": True, "use_web_search": False}
        },
        {
            "query": "what is our password policy",
            "expected": "rag",
            "should_use": {"use_rag": True, "use_logs": False, "use_web_search": False}
        },
        {
            "query": "latest ransomware threats",
            "expected": "web_search",
            "should_use": {"use_rag": False, "use_logs": False, "use_web_search": True}
        },
        {
            "query": "check IP reputation for 1.2.3.4",
            "expected": "web_search",
            "should_use": {"use_rag": False, "use_logs": False, "use_web_search": True}
        }
    ]

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\n[Test {i}] Query: \"{test['query']}\"")
        print(f"  Expected route: {test['expected']}")

        result = decide_tools(test['query'])

        print(f"  Actual result:")
        print(f"    use_rag: {result.get('use_rag')}")
        print(f"    use_logs: {result.get('use_logs')}")
        print(f"    use_web_search: {result.get('use_web_search')}")
        print(f"    reason: {result.get('reason')}")

        # Check if routing matches expectations
        expected = test['should_use']
        matches = (
            result.get('use_rag') == expected['use_rag'] and
            result.get('use_logs') == expected['use_logs'] and
            result.get('use_web_search') == expected['use_web_search']
        )

        if matches:
            print(f"  ✓ PASS: Correctly routed to {test['expected']}")
            passed += 1
        else:
            print(f"  ✗ FAIL: Expected {expected}, got {result}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("\nCVE and vulnerability queries now correctly route to web search!")
        print("The agent will no longer search authentication logs for CVE queries.")
        return 0
    else:
        print(f"\n✗ {failed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(test_routing())
