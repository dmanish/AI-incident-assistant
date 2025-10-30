#!/usr/bin/env python3
"""
Debug DuckDuckGo API to understand why it returns blank results
"""

import requests
import json

def test_duckduckgo_api():
    """Test DuckDuckGo API with CVE queries"""

    test_queries = [
        "any vulnerabilities reported this year on glibc",
        "CVE glibc 2024",
        "is there a CVE on TLS",
        "what vulnerability was reported this month on TCP"
    ]

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    print("=" * 70)
    print("Testing DuckDuckGo Instant Answer API")
    print("=" * 70)

    for query in test_queries:
        print(f"\n{'=' * 70}")
        print(f"Query: {query}")
        print("=" * 70)

        try:
            # Test with enhanced query
            enhanced_query = f"{query} CVE vulnerability security advisory"
            params = {'q': enhanced_query, 'format': 'json'}

            print(f"Enhanced query: {enhanced_query}")
            print(f"URL: https://api.duckduckgo.com/")
            print(f"Params: {params}")

            response = requests.get(
                'https://api.duckduckgo.com/',
                params=params,
                headers=headers,
                timeout=10
            )

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                print(f"\nResponse keys: {list(data.keys())}")

                # Check what we're getting
                abstract = data.get('AbstractText', '')
                abstract_source = data.get('AbstractSource', '')
                abstract_url = data.get('AbstractURL', '')
                related = data.get('RelatedTopics', [])
                answer = data.get('Answer', '')
                definition = data.get('Definition', '')

                print(f"\nAbstractText: {abstract[:200] if abstract else '(empty)'}")
                print(f"AbstractSource: {abstract_source}")
                print(f"AbstractURL: {abstract_url}")
                print(f"Answer: {answer[:200] if answer else '(empty)'}")
                print(f"Definition: {definition[:200] if definition else '(empty)'}")
                print(f"RelatedTopics count: {len(related)}")

                if related:
                    print("\nFirst 3 RelatedTopics:")
                    for i, topic in enumerate(related[:3]):
                        if isinstance(topic, dict):
                            topic_text = topic.get('Text', '')
                            topic_url = topic.get('FirstURL', '')
                            print(f"  {i+1}. {topic_text[:100]}")
                            print(f"     URL: {topic_url}")

                # Show full JSON for first query
                if query == test_queries[0]:
                    print("\n" + "=" * 70)
                    print("FULL JSON RESPONSE (first query only):")
                    print("=" * 70)
                    print(json.dumps(data, indent=2))

            else:
                print(f"ERROR: Status {response.status_code}")
                print(response.text[:500])

        except Exception as e:
            print(f"ERROR: {e}")

    print("\n" + "=" * 70)
    print("CONCLUSION:")
    print("=" * 70)
    print("DuckDuckGo Instant Answer API is designed for instant answers")
    print("(like 'what is the capital of France'), NOT for real-time")
    print("threat intelligence or CVE lookups.")
    print("\nWe need a different approach for web search.")

if __name__ == "__main__":
    test_duckduckgo_api()
