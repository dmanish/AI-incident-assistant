#!/usr/bin/env python3
"""Debug DuckDuckGo search to see what's happening"""

import requests
import re


def test_duckduckgo():
    query = "how many CVE were reported on glib this year"

    print(f"Testing DuckDuckGo search for: {query}")
    print("=" * 60)

    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        data = {'q': query}

        print(f"Sending POST request to: {url}")
        print(f"Query: {query}")

        response = requests.post(url, headers=headers, data=data, timeout=10)

        print(f"Response status: {response.status_code}")
        print(f"Response length: {len(response.text)} chars")

        if response.status_code == 200:
            html = response.text

            # Try to extract results
            result_pattern = r'<div class="result__body">.*?<a class="result__a" href="(.*?)".*?>(.*?)</a>.*?<a class="result__snippet".*?>(.*?)</a>'
            matches = re.findall(result_pattern, html, re.DOTALL)

            print(f"\nFound {len(matches)} results using regex pattern")

            if matches:
                print("\nFirst 3 results:")
                for i, match in enumerate(matches[:3], 1):
                    url_match, title_match, snippet_match = match
                    # Clean HTML tags
                    title = re.sub(r'<.*?>', '', title_match).strip()[:100]
                    snippet = re.sub(r'<.*?>', '', snippet_match).strip()[:150]
                    print(f"\n{i}. {title}")
                    print(f"   {snippet}")
                    print(f"   URL: {url_match[:80]}")
            else:
                print("\n⚠️  No results found with regex pattern")
                print("Let's check if HTML structure changed...")

                # Debug: Check what's in the HTML
                if 'result__body' in html:
                    print("✓ 'result__body' found in HTML")
                else:
                    print("✗ 'result__body' NOT found in HTML")

                if 'result__a' in html:
                    print("✓ 'result__a' found in HTML")
                else:
                    print("✗ 'result__a' NOT found in HTML")

                # Try to find any <a> tags
                links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html)
                print(f"\nFound {len(links)} total <a> tags in HTML")

                # Save HTML for inspection
                with open('/tmp/duckduckgo_response.html', 'w') as f:
                    f.write(html)
                print("\n📄 Saved HTML response to /tmp/duckduckgo_response.html for inspection")

        else:
            print(f"❌ Request failed with status {response.status_code}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_duckduckgo()
