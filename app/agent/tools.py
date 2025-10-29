# app/agent/tools.py
"""
Tool definitions for OpenAI function calling API
Each tool has a schema and an execution function
"""

from typing import Dict, Any, List
import json

# Tool schemas in OpenAI format
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "query_failed_logins",
            "description": "Search authentication logs for failed login attempts. Use this when user asks about failed logins, login attempts, authentication failures, or wants to see logs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "ISO date (YYYY-MM-DD) to search. Use 'today' for current date, or specific date like '2025-10-28'"
                    },
                    "username": {
                        "type": "string",
                        "description": "Optional: specific username to filter (e.g., 'jdoe', 'alice')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 200
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search security policies, incident response playbooks, and knowledge base articles using semantic search (RAG). Use this when user asks 'how to', 'what is the policy', 'what should I do', or needs procedural guidance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query - what the user wants to know about policies/procedures"
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

    if tool_name == "query_failed_logins":
        if isinstance(result, dict):
            count = result.get("count", 0)
            sample = result.get("sample", [])
            username = result.get("username", "any")
            date = result.get("date", "unknown")

            output = f"Log Query Results:\n"
            output += f"- Date: {date}\n"
            output += f"- Username filter: {username}\n"
            output += f"- Total failed login attempts: {count}\n\n"

            if sample and len(sample) > 0:
                output += f"Sample entries (showing {len(sample)}):\n"
                for i, entry in enumerate(sample[:5], 1):
                    output += f"{i}. {entry.get('timestamp', 'N/A')} - User: {entry.get('user', 'N/A')}, IP: {entry.get('ip', 'N/A')}\n"
            else:
                output += "No failed login attempts found for these filters.\n"

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
                    text = chunk.get("text", "")[:500]  # Limit text length
                    output += f"\n{i}. Source: {source}\n{text}\n"
            else:
                output += "No relevant documents found in knowledge base.\n"

            return output
        return str(result)

    return json.dumps(result, default=str)
