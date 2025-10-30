#!/usr/bin/env python3
"""
Test improved web search implementation
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_web_search():
    """Test the improved web search with real queries"""
    from app.utils.web_search import search_threat_intelligence, format_search_results

    print("=" * 70)
    print("Testing Improved Web Search (NVD + DuckDuckGo HTML)")
    print("=" * 70)

    test_cases = [
        {
            "query": "any vulnerabilities reported this year on glibc",
            "search_type": "cve",
            "description": "User's original failing query"
        },
        {
            "query": "CVE-2024-6387",
            "search_type": "cve",
            "description": "Specific CVE lookup"
        },
        {
            "query": "is there a CVE on TLS",
            "search_type": "cve",
            "description": "General CVE search"
        },
        {
            "query": "OpenSSL vulnerabilities 2024",
            "search_type": "cve",
            "description": "Product vulnerability search"
        }
    ]

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'=' * 70}")
        print(f"[Test {i}] {test['description']}")
        print(f"Query: \"{test['query']}\"")
        print(f"Search Type: {test['search_type']}")
        print("=" * 70)

        try:
            # Execute search
            search_response = search_threat_intelligence(
                query=test['query'],
                search_type=test['search_type'],
                max_results=3
            )

            # Show results
            result_count = search_response.get('result_count', 0)
            source = search_response.get('source', 'unknown')

            print(f"\nSource: {source}")
            print(f"Results found: {result_count}")

            if result_count > 0:
                print("\n✓ SUCCESS: Found results!")
                results = search_response.get('results', [])
                for j, result in enumerate(results[:3], 1):
                    print(f"\n{j}. {result.get('title', 'No title')}")
                    snippet = result.get('snippet', '')
                    print(f"   {snippet[:150]}...")
                    print(f"   URL: {result.get('url', 'N/A')}")
                passed += 1
            else:
                print("\n✗ FAILED: No results returned")
                failed += 1

            # Also test formatting
            print("\n" + "-" * 70)
            print("Formatted output (for LLM):")
            print("-" * 70)
            formatted = format_search_results(search_response)
            print(formatted[:500] + "..." if len(formatted) > 500 else formatted)

        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("\nThe improved web search now returns actual CVE results!")
        print("NVD (NIST) is used for CVE queries, with fallback to DuckDuckGo.")
        return 0
    else:
        print(f"\n✗ {failed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(test_web_search())
