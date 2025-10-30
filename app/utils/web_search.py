"""
Web search utilities for threat intelligence
Uses multiple strategies based on query type
"""

import requests
from typing import List, Dict, Any, Optional
import json
import re
from datetime import datetime


def search_cve_nvd(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search NVD (National Vulnerability Database) for CVE information
    API: https://nvd.nist.gov/developers/vulnerabilities
    """
    results = []

    try:
        # Extract CVE ID if present (e.g., CVE-2024-1234)
        cve_pattern = r'CVE-\d{4}-\d{4,7}'
        cve_matches = re.findall(cve_pattern, query.upper())

        if cve_matches:
            # Direct CVE lookup
            for cve_id in cve_matches[:max_results]:
                try:
                    url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
                    headers = {'User-Agent': 'Mozilla/5.0 (AI Security Assistant)'}
                    response = requests.get(url, headers=headers, timeout=10)

                    if response.status_code == 200:
                        data = response.json()
                        vulnerabilities = data.get('vulnerabilities', [])

                        for vuln in vulnerabilities:
                            cve_data = vuln.get('cve', {})
                            description = ''
                            descriptions = cve_data.get('descriptions', [])
                            for desc in descriptions:
                                if desc.get('lang') == 'en':
                                    description = desc.get('value', '')
                                    break

                            published = cve_data.get('published', '')
                            results.append({
                                'title': cve_id,
                                'snippet': description[:500],
                                'url': f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                                'source': 'NVD (NIST)',
                                'published': published
                            })
                except Exception:
                    continue
        else:
            # Keyword search - extract product/technology name
            keywords = query.lower()
            # Remove common words
            for word in ['cve', 'vulnerability', 'vulnerabilities', 'reported', 'on', 'in', 'for', 'this', 'year', 'month']:
                keywords = keywords.replace(word, '')
            keywords = keywords.strip()

            if keywords:
                # Use keyword search API
                url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
                params = {
                    'keywordSearch': keywords,
                    'resultsPerPage': max_results
                }
                headers = {'User-Agent': 'Mozilla/5.0 (AI Security Assistant)'}
                response = requests.get(url, params=params, headers=headers, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    vulnerabilities = data.get('vulnerabilities', [])

                    for vuln in vulnerabilities:
                        cve_data = vuln.get('cve', {})
                        cve_id = cve_data.get('id', '')
                        description = ''
                        descriptions = cve_data.get('descriptions', [])
                        for desc in descriptions:
                            if desc.get('lang') == 'en':
                                description = desc.get('value', '')
                                break

                        published = cve_data.get('published', '')

                        # Get CVSS score if available
                        metrics = cve_data.get('metrics', {})
                        cvss_score = 'N/A'
                        for metric_key in ['cvssMetricV31', 'cvssMetricV30', 'cvssMetricV2']:
                            if metric_key in metrics and metrics[metric_key]:
                                cvss_data = metrics[metric_key][0].get('cvssData', {})
                                cvss_score = cvss_data.get('baseScore', 'N/A')
                                break

                        results.append({
                            'title': f"{cve_id} (CVSS: {cvss_score})",
                            'snippet': description[:500],
                            'url': f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                            'source': 'NVD (NIST)',
                            'published': published
                        })
    except Exception as e:
        # If NVD fails, return empty (will fall back to general search)
        pass

    return results


def search_duckduckgo_html(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search using DuckDuckGo HTML (actual search results, not Instant Answer API)
    """
    results = []

    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        data = {'q': query}

        response = requests.post(url, headers=headers, data=data, timeout=10)

        if response.status_code == 200:
            html = response.text

            # Parse results using simple regex (not perfect but works)
            # Extract result blocks
            result_pattern = r'<div class="result__body">.*?<a class="result__a" href="(.*?)".*?>(.*?)</a>.*?<a class="result__snippet".*?>(.*?)</a>'
            matches = re.findall(result_pattern, html, re.DOTALL)

            for i, match in enumerate(matches[:max_results]):
                url_match, title_match, snippet_match = match

                # Clean HTML tags from title and snippet
                title = re.sub(r'<.*?>', '', title_match).strip()
                snippet = re.sub(r'<.*?>', '', snippet_match).strip()

                # Decode HTML entities
                title = title.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
                snippet = snippet.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')

                results.append({
                    'title': title[:200],
                    'snippet': snippet[:500],
                    'url': url_match,
                    'source': 'DuckDuckGo Search'
                })
    except Exception:
        pass

    return results


def search_threat_intelligence(
    query: str,
    search_type: str = "general",
    max_results: int = 5
) -> Dict[str, Any]:
    """
    Main entry point for threat intelligence search

    Args:
        query: Search query
        search_type: "cve" | "ip_reputation" | "domain_reputation" | "general"
        max_results: Maximum number of results to return

    Returns:
        {
            "results": List[Dict],
            "query": str,
            "search_type": str,
            "source": str,
            "timestamp": str
        }
    """
    results = []
    source = "unknown"

    # Strategy 1: For CVE queries, try NVD first
    # Only use NVD if search_type is explicitly "cve" (specific CVE lookup)
    # Don't use NVD for general questions about CVEs (counting, statistics, etc.)
    if search_type == "cve":
        results = search_cve_nvd(query, max_results)
        if results:
            source = "NVD (NIST)"

    # Strategy 2: If NVD didn't return results, or if using general search, use DuckDuckGo
    if not results:
        # Enhance query for better results
        if search_type == "cve":
            enhanced_query = f"{query} site:nvd.nist.gov OR site:cve.org OR site:cve.mitre.org"
        elif search_type == "ip_reputation":
            enhanced_query = f"{query} site:abuseipdb.com OR site:virustotal.com OR malicious"
        elif search_type == "domain_reputation":
            enhanced_query = f"{query} site:virustotal.com OR site:urlhaus.abuse.ch OR malicious"
        else:
            enhanced_query = query

        results = search_duckduckgo_html(enhanced_query, max_results)
        if results:
            source = "DuckDuckGo Search"

    return {
        "results": results,
        "query": query,
        "search_type": search_type,
        "source": source,
        "timestamp": datetime.utcnow().isoformat(),
        "result_count": len(results)
    }


def format_search_results(search_response: Dict[str, Any]) -> str:
    """
    Format search results for LLM consumption
    """
    results = search_response.get('results', [])
    query = search_response.get('query', '')
    source = search_response.get('source', '')

    if not results:
        return (
            f"\n---\nTool: web_search\n"
            f"Query: {query}\n"
            f"No specific results found.\n"
            f"Recommendation: Check security databases directly:\n"
            f"- CVE information: https://nvd.nist.gov/\n"
            f"- IP reputation: https://www.abuseipdb.com/\n"
            f"- Domain reputation: https://www.virustotal.com/\n"
        )

    formatted = f"\n---\nTool: web_search\nQuery: {query}\nSource: {source}\nFound: {len(results)} results\n\n"

    for i, result in enumerate(results, 1):
        title = result.get('title', 'Result')
        snippet = result.get('snippet', '')
        url = result.get('url', '')
        published = result.get('published', '')

        formatted += f"{i}. {title}\n"
        if published:
            formatted += f"   Published: {published}\n"
        formatted += f"   {snippet[:400]}\n"
        formatted += f"   URL: {url}\n\n"

    return formatted
