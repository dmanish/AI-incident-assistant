#!/usr/bin/env python3
"""
Test that CVE count queries use general web search, not specific CVE lookup
"""

from app.utils.web_search import search_threat_intelligence


def test_cve_count_query():
    """Test that 'how many CVEs' queries work correctly"""

    query = "how many CVE were reported on glib this year"

    # Test 1: Explicit general search (what LLM should choose now)
    print("Test 1: Using search_type='general' (correct behavior)")
    print("=" * 60)
    result = search_threat_intelligence(
        query=query,
        search_type="general",  # This is what we want the LLM to choose
        max_results=5
    )

    print(f"Query: {result['query']}")
    print(f"Search type: {result['search_type']}")
    print(f"Source: {result['source']}")
    print(f"Result count: {result['result_count']}")
    print()

    if result['results']:
        print("Sample results:")
        for i, r in enumerate(result['results'][:3], 1):
            print(f"{i}. {r['title'][:80]}")
            print(f"   {r['url']}")
    else:
        print("No results returned")

    print("\n" + "=" * 60 + "\n")

    # Test 2: Show what happens with search_type='cve' (incorrect)
    print("Test 2: Using search_type='cve' (incorrect for this query)")
    print("=" * 60)
    result2 = search_threat_intelligence(
        query=query,
        search_type="cve",  # Wrong choice
        max_results=5
    )

    print(f"Query: {result2['query']}")
    print(f"Search type: {result2['search_type']}")
    print(f"Source: {result2['source']}")
    print(f"Result count: {result2['result_count']}")
    print()

    if result2['results']:
        print("Sample results:")
        for i, r in enumerate(result2['results'][:3], 1):
            print(f"{i}. {r['title'][:80]}")
            print(f"   {r['url']}")
    else:
        print("No results returned (expected - NVD API not good for counting)")

    print("\n" + "=" * 60 + "\n")

    # Verify the fix
    if result['source'] == 'DuckDuckGo Search' and result['result_count'] > 0:
        print("✅ SUCCESS: General search returned web results")
    else:
        print("❌ ISSUE: General search didn't return expected results")

    print("\nExpected behavior:")
    print("- LLM should choose search_type='general' for 'how many CVE' queries")
    print("- This will trigger DuckDuckGo web search")
    print("- Results should include articles/pages with CVE statistics")
    print("\nIncorrect behavior (before fix):")
    print("- LLM was choosing search_type='cve'")
    print("- This triggered NVD API keyword search")
    print("- NVD API is not designed for counting/statistics queries")


if __name__ == "__main__":
    test_cve_count_query()
