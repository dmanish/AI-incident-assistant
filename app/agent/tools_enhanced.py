# app/agent/tools_enhanced.py
"""
Enhanced tool definitions with more flexibility and web search capability
Backward compatible with existing tools but with expanded functionality
"""

from typing import Dict, Any, List

# Enhanced tool schemas in OpenAI format
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_authentication_logs",
            "description": """Search authentication logs for login attempts, session activity, and authentication events.
Use this when user asks about logins (failed/successful), authentication patterns, session activity,
or wants to investigate user/IP behavior. Supports filtering by result type, user, IP, and date ranges.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_start": {
                        "type": "string",
                        "description": """Start date for search. Accepts:
- ISO date: '2025-10-28'
- Relative: 'today', 'yesterday', 'last_7_days', 'last_30_days', 'this_week', 'this_month'
Defaults to 'today'"""
                    },
                    "date_end": {
                        "type": "string",
                        "description": "Optional end date (ISO format or relative). If not specified, uses date_start"
                    },
                    "result_filter": {
                        "type": "string",
                        "enum": ["failed", "successful", "all"],
                        "description": "Filter by authentication result. 'failed' = failed attempts, 'successful' = successful logins, 'all' = both",
                        "default": "failed"
                    },
                    "username": {
                        "type": "string",
                        "description": "Optional: filter by specific username (e.g., 'jdoe', 'alice')"
                    },
                    "ip_address": {
                        "type": "string",
                        "description": "Optional: filter by IP address (e.g., '192.168.1.100')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of raw results to return",
                        "default": 200
                    },
                    "aggregate_by": {
                        "type": "string",
                        "enum": ["none", "user", "ip", "hour", "day"],
                        "description": "Group results by field. 'none' = raw logs, 'user' = count by user, 'ip' = count by IP, 'hour' = hourly counts, 'day' = daily counts",
                        "default": "none"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": """Search security policies, incident response playbooks, and knowledge base articles using semantic search (RAG).
Use this when user asks 'how to', 'what is the policy', 'what should I do', or needs procedural guidance,
compliance information, or security best practices.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query - what the user wants to know about policies/procedures/security guidance"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of relevant documents to retrieve",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_threat_intelligence",
            "description": """Search external threat intelligence sources for CVEs, security advisories, IP reputation,
domain analysis, and current threat landscape. Use this when user asks about:
- CVE vulnerabilities or security advisories
- IP address reputation or geolocation
- Domain/URL analysis or reputation
- Latest threats, attacks, or exploits
- Security news or threat actor information
Note: This tool searches external sources, not internal logs.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for threat intelligence (e.g., 'CVE-2024-1234', 'IP 1.2.3.4 reputation', 'latest ransomware threats')"
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["general", "cve", "ip_reputation", "domain_reputation"],
                        "description": """Type of search to perform:
- 'general': Broad threat intel, vulnerability counts, security news, general questions about CVEs/threats (DEFAULT - use when in doubt)
- 'cve': ONLY for looking up a SPECIFIC CVE ID (e.g., CVE-2024-1234). Do NOT use for counting CVEs or asking 'how many CVEs'
- 'ip_reputation': IP address analysis/reputation lookup
- 'domain_reputation': Domain/URL analysis or reputation check""",
                        "default": "general"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def get_tool_by_name(name: str) -> Dict[str, Any]:
    """Get tool definition by name"""
    for tool in TOOL_DEFINITIONS:
        if tool["function"]["name"] == name:
            return tool
    raise ValueError(f"Tool {name} not found")


def format_tool_result(tool_name: str, result: Any, success: bool = True) -> str:
    """
    Format tool execution result for LLM consumption
    Returns a concise, structured string
    """
    if not success:
        return f"Error executing {tool_name}: {result}"

    if tool_name == "search_authentication_logs":
        if isinstance(result, dict):
            count = result.get("count", 0)
            sample = result.get("sample", [])
            date_range = result.get("date_range", {})
            filters = result.get("filters", {})
            aggregation = result.get("aggregation", [])

            output = f"Authentication Log Search Results:\n"
            output += f"- Date range: {date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}\n"
            output += f"- Result filter: {filters.get('result_filter', 'N/A')}\n"
            if filters.get('username'):
                output += f"- Username filter: {filters['username']}\n"
            if filters.get('ip_address'):
                output += f"- IP filter: {filters['ip_address']}\n"
            output += f"- Total matching records: {count}\n\n"

            # Show aggregation if present
            if aggregation:
                output += f"Aggregated data:\n"
                for item in aggregation[:10]:
                    group_key = item.get('group_key', 'N/A')
                    count_val = item.get('count', 0)
                    output += f"  - {group_key}: {count_val} events\n"
                output += "\n"

            # Show sample raw logs
            if sample and len(sample) > 0:
                output += f"Sample log entries (showing {len(sample)}):\n"
                for i, entry in enumerate(sample[:5], 1):
                    ts = entry.get('timestamp', 'N/A')
                    user = entry.get('user', 'N/A')
                    ip = entry.get('ip', 'N/A')
                    result_val = entry.get('result', 'N/A')
                    output += f"{i}. [{ts}] User: {user}, IP: {ip}, Result: {result_val}\n"
            else:
                output += "No matching log entries found for these filters.\n"

            return output
        return str(result)

    elif tool_name == "search_knowledge_base":
        if isinstance(result, dict):
            chunks = result.get("chunks", [])
            count = result.get("count", 0)

            output = f"Knowledge Base Search Results:\n"
            output += f"- Found {count} relevant documents\n\n"

            if chunks:
                output += "Relevant content:\n"
                for i, chunk in enumerate(chunks[:3], 1):
                    source = chunk.get("source", "unknown")
                    text = chunk.get("text", "")[:500]
                    output += f"\n{i}. Source: {source}\n{text}\n"
            else:
                output += "No relevant documents found in knowledge base.\n"

            return output
        return str(result)

    elif tool_name == "search_threat_intelligence":
        if isinstance(result, dict):
            if result.get("error"):
                return f"Threat intelligence search error: {result['error']}"

            query = result.get("query", "")
            search_type = result.get("search_type", "general")
            results = result.get("results", [])

            output = f"Threat Intelligence Search Results:\n"
            output += f"- Query: {query}\n"
            output += f"- Search type: {search_type}\n"
            output += f"- Found {len(results)} results\n\n"

            if results:
                for i, item in enumerate(results[:5], 1):
                    title = item.get("title", "N/A")
                    snippet = item.get("snippet", "")[:300]
                    url = item.get("url", "")
                    output += f"\n{i}. {title}\n"
                    if snippet:
                        output += f"   {snippet}\n"
                    if url:
                        output += f"   Source: {url}\n"
            else:
                output += "No threat intelligence found for this query.\n"

            return output
        return str(result)

    # Default JSON formatting
    import json
    return json.dumps(result, default=str)
