# app/agent/executors.py
"""
Tool executors that integrate with existing codebase
Handles RBAC, parameter processing, and calls to actual tool functions
"""

from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd


class ToolExecutors:
    """
    Wrapper class for tool execution with RBAC integration
    """

    def __init__(
        self,
        retrieve_chunks_fn,
        query_failed_logins_fn,
        role_allows_tool_fn,
        role_allows_doc_fn
    ):
        """
        Initialize with references to main.py functions

        Args:
            retrieve_chunks_fn: Function to retrieve RAG chunks
            query_failed_logins_fn: Function to query logs
            role_allows_tool_fn: RBAC check for tools
            role_allows_doc_fn: RBAC check for documents
        """
        self.retrieve_chunks = retrieve_chunks_fn
        self.query_failed_logins = query_failed_logins_fn
        self.role_allows_tool = role_allows_tool_fn
        self.role_allows_doc = role_allows_doc_fn

    def execute_search_knowledge_base(
        self,
        arguments: Dict[str, Any],
        role: str
    ) -> Dict[str, Any]:
        """
        Execute knowledge base search with RAG

        Args:
            arguments: {"query": str, "top_k": int}
            role: User role for RBAC

        Returns:
            Dict with search results
        """
        query = arguments.get("query", "")
        top_k = arguments.get("top_k", 5)

        if not query:
            return {
                "count": 0,
                "chunks": [],
                "error": "No query provided"
            }

        try:
            # Call existing retrieve_chunks function
            chunks = self.retrieve_chunks(query, role=role, top_k=top_k)

            # Format for agent consumption
            formatted_chunks = []
            for chunk in chunks:
                metadata = chunk.get("metadata", {})
                formatted_chunks.append({
                    "source": metadata.get("source_path", "unknown"),
                    "doc_type": metadata.get("doc_type", "kb"),
                    "text": chunk.get("text", "")[:800],  # Limit text length
                    "score": chunk.get("score")
                })

            return {
                "count": len(formatted_chunks),
                "chunks": formatted_chunks,
                "query": query
            }

        except Exception as e:
            return {
                "count": 0,
                "chunks": [],
                "error": str(e)
            }

    def execute_query_failed_logins(
        self,
        arguments: Dict[str, Any],
        role: str
    ) -> Dict[str, Any]:
        """
        Execute log query for failed logins

        Args:
            arguments: {"date": str, "username": Optional[str], "limit": int}
            role: User role for RBAC

        Returns:
            Dict with query results
        """
        # RBAC check
        if not self.role_allows_tool(role, "log_query"):
            raise PermissionError(
                f"Role '{role}' is not authorized to query logs. "
                "Only security and engineering roles can access logs."
            )

        # Parse arguments
        date_arg = arguments.get("date", "")
        username = arguments.get("username")
        limit = arguments.get("limit", 200)

        # Handle "today" or relative dates
        if date_arg.lower() == "today":
            date_iso = datetime.utcnow().date().isoformat()
        elif date_arg.lower() == "yesterday":
            from datetime import timedelta
            date_iso = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
        else:
            date_iso = date_arg  # Assume it's already ISO format

        try:
            # Call existing query_failed_logins function
            df = self.query_failed_logins(
                date_iso=date_iso,
                username=username,
                limit=limit
            )

            # Convert to dict for JSON serialization
            if isinstance(df, pd.DataFrame):
                count = len(df)
                sample = df.head(10).to_dict(orient="records")
            else:
                count = 0
                sample = []

            return {
                "count": count,
                "date": date_iso,
                "username": username or "any",
                "sample": sample,
                "total_in_sample": len(sample)
            }

        except Exception as e:
            return {
                "count": 0,
                "date": date_iso,
                "username": username,
                "sample": [],
                "error": str(e)
            }

    def get_executors(self) -> Dict[str, Any]:
        """
        Get dict of tool name -> executor function

        Returns:
            Dict mapping tool names to executor functions
        """
        return {
            "search_knowledge_base": self.execute_search_knowledge_base,
            "query_failed_logins": self.execute_query_failed_logins
        }


def create_tool_executors(
    retrieve_chunks_fn,
    query_failed_logins_fn,
    role_allows_tool_fn,
    role_allows_doc_fn
) -> Dict[str, Any]:
    """
    Factory function to create tool executors

    Returns:
        Dict of tool_name -> executor_function
    """
    executors = ToolExecutors(
        retrieve_chunks_fn=retrieve_chunks_fn,
        query_failed_logins_fn=query_failed_logins_fn,
        role_allows_tool_fn=role_allows_tool_fn,
        role_allows_doc_fn=role_allows_doc_fn
    )
    return executors.get_executors()
