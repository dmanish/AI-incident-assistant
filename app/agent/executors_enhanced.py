# app/agent/executors_enhanced.py
"""
Enhanced tool executors with improved functionality:
- Flexible authentication log search (failed/successful/all, date ranges, aggregation)
- Web-based threat intelligence search
- Better date parsing and filtering
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import pandas as pd
import os
import requests


class EnhancedToolExecutors:
    """
    Enhanced wrapper class for tool execution with RBAC integration
    """

    def __init__(
        self,
        retrieve_chunks_fn,
        query_logs_fn,  # More generic now
        role_allows_tool_fn,
        role_allows_doc_fn
    ):
        """
        Initialize with references to main.py functions

        Args:
            retrieve_chunks_fn: Function to retrieve RAG chunks
            query_logs_fn: Function to query logs (should accept flexible params)
            role_allows_tool_fn: RBAC check for tools
            role_allows_doc_fn: RBAC check for documents
        """
        self.retrieve_chunks = retrieve_chunks_fn
        self.query_logs = query_logs_fn
        self.role_allows_tool = role_allows_tool_fn
        self.role_allows_doc = role_allows_doc_fn

    def _parse_relative_date(self, date_str: str) -> str:
        """
        Parse relative date strings to ISO format

        Args:
            date_str: Date string (ISO or relative like 'today', 'yesterday', etc.)

        Returns:
            ISO date string (YYYY-MM-DD)
        """
        date_str = (date_str or "today").lower().strip()
        today = datetime.utcnow().date()

        if date_str == "today":
            return today.isoformat()
        elif date_str == "yesterday":
            return (today - timedelta(days=1)).isoformat()
        elif date_str == "last_7_days" or date_str == "last_week":
            return (today - timedelta(days=7)).isoformat()
        elif date_str == "last_30_days" or date_str == "last_month":
            return (today - timedelta(days=30)).isoformat()
        elif date_str == "this_week":
            # Start of current week (Monday)
            days_since_monday = today.weekday()
            return (today - timedelta(days=days_since_monday)).isoformat()
        elif date_str == "this_month":
            return today.replace(day=1).isoformat()
        else:
            # Assume it's already ISO format or parseable
            try:
                parsed = datetime.fromisoformat(date_str)
                return parsed.date().isoformat()
            except:
                # Default to today if unparseable
                return today.isoformat()

    def execute_search_knowledge_base(
        self,
        arguments: Dict[str, Any],
        role: str
    ) -> Dict[str, Any]:
        """
        Execute knowledge base search with RAG (unchanged from original)

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
                    "text": chunk.get("text", "")[:800],
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

    def execute_search_authentication_logs(
        self,
        arguments: Dict[str, Any],
        role: str
    ) -> Dict[str, Any]:
        """
        Enhanced authentication log search with flexible filtering and aggregation

        Args:
            arguments: {
                "date_start": str,
                "date_end": Optional[str],
                "result_filter": "failed" | "successful" | "all",
                "username": Optional[str],
                "ip_address": Optional[str],
                "limit": int,
                "aggregate_by": "none" | "user" | "ip" | "hour" | "day"
            }
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
        date_start_arg = arguments.get("date_start", "today")
        date_end_arg = arguments.get("date_end")
        result_filter = arguments.get("result_filter", "failed").lower()
        username = arguments.get("username")
        ip_address = arguments.get("ip_address")
        limit = arguments.get("limit", 200)
        aggregate_by = arguments.get("aggregate_by", "none").lower()

        # Parse dates
        date_start = self._parse_relative_date(date_start_arg)
        date_end = self._parse_relative_date(date_end_arg) if date_end_arg else date_start

        try:
            # Call the log query function with enhanced parameters
            df = self.query_logs(
                date_start=date_start,
                date_end=date_end,
                result_filter=result_filter,
                username=username,
                ip_address=ip_address,
                limit=limit
            )

            # Handle empty results
            if df is None or (isinstance(df, pd.DataFrame) and len(df) == 0):
                return {
                    "count": 0,
                    "date_range": {"start": date_start, "end": date_end},
                    "filters": {
                        "result_filter": result_filter,
                        "username": username,
                        "ip_address": ip_address
                    },
                    "sample": [],
                    "aggregation": []
                }

            # Convert to DataFrame if needed
            if not isinstance(df, pd.DataFrame):
                df = pd.DataFrame(df)

            count = len(df)
            sample = df.head(10).to_dict(orient="records") if count > 0 else []

            # Perform aggregation if requested
            aggregation = []
            if aggregate_by != "none" and count > 0:
                try:
                    if aggregate_by == "user" and "user" in df.columns:
                        agg_df = df.groupby("user").size().reset_index(name="count")
                        agg_df = agg_df.sort_values("count", ascending=False).head(20)
                        aggregation = [
                            {"group_key": row["user"], "count": int(row["count"])}
                            for _, row in agg_df.iterrows()
                        ]
                    elif aggregate_by == "ip" and "ip" in df.columns:
                        agg_df = df.groupby("ip").size().reset_index(name="count")
                        agg_df = agg_df.sort_values("count", ascending=False).head(20)
                        aggregation = [
                            {"group_key": row["ip"], "count": int(row["count"])}
                            for _, row in agg_df.iterrows()
                        ]
                    elif aggregate_by in ["hour", "day"] and "timestamp" in df.columns:
                        # Convert timestamp to datetime if it's not already
                        df["timestamp"] = pd.to_datetime(df["timestamp"])
                        if aggregate_by == "hour":
                            df["time_group"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:00")
                        else:  # day
                            df["time_group"] = df["timestamp"].dt.strftime("%Y-%m-%d")
                        agg_df = df.groupby("time_group").size().reset_index(name="count")
                        agg_df = agg_df.sort_values("time_group").tail(20)
                        aggregation = [
                            {"group_key": row["time_group"], "count": int(row["count"])}
                            for _, row in agg_df.iterrows()
                        ]
                except Exception as agg_error:
                    # If aggregation fails, continue without it
                    pass

            return {
                "count": count,
                "date_range": {"start": date_start, "end": date_end},
                "filters": {
                    "result_filter": result_filter,
                    "username": username,
                    "ip_address": ip_address
                },
                "sample": sample,
                "aggregation": aggregation
            }

        except Exception as e:
            return {
                "count": 0,
                "date_range": {"start": date_start, "end": date_end},
                "filters": {
                    "result_filter": result_filter,
                    "username": username,
                    "ip_address": ip_address
                },
                "sample": [],
                "aggregation": [],
                "error": str(e)
            }

    def execute_search_threat_intelligence(
        self,
        arguments: Dict[str, Any],
        role: str
    ) -> Dict[str, Any]:
        """
        Search external threat intelligence using DuckDuckGo (free, no API key)

        Args:
            arguments: {
                "query": str,
                "search_type": "general" | "cve" | "ip_reputation" | "domain_reputation",
                "max_results": int
            }
            role: User role for RBAC

        Returns:
            Dict with search results
        """
        query = arguments.get("query", "")
        search_type = arguments.get("search_type", "general")
        max_results = arguments.get("max_results", 5)

        if not query:
            return {
                "query": query,
                "search_type": search_type,
                "results": [],
                "error": "No query provided"
            }

        try:
            # Use improved web search module (NVD + DuckDuckGo HTML)
            from app.utils.web_search import search_threat_intelligence

            search_response = search_threat_intelligence(
                query=query,
                search_type=search_type,
                max_results=max_results
            )

            return {
                "query": query,
                "search_type": search_type,
                "results": search_response.get('results', []),
                "source": search_response.get('source', 'Web Search'),
                "result_count": search_response.get('result_count', 0)
            }

        except Exception as e:
            return {
                "query": query,
                "search_type": search_type,
                "results": [],
                "error": f"Search failed: {str(e)}",
                "source": "Error"
            }

    def get_executors(self) -> Dict[str, Any]:
        """
        Get dict of tool name -> executor function

        Returns:
            Dict mapping tool names to executor functions
        """
        return {
            "search_knowledge_base": self.execute_search_knowledge_base,
            "search_authentication_logs": self.execute_search_authentication_logs,
            "search_threat_intelligence": self.execute_search_threat_intelligence
        }


def create_enhanced_tool_executors(
    retrieve_chunks_fn,
    query_logs_fn,
    role_allows_tool_fn,
    role_allows_doc_fn
) -> Dict[str, Any]:
    """
    Factory function to create enhanced tool executors

    Returns:
        Dict of tool_name -> executor_function
    """
    executors = EnhancedToolExecutors(
        retrieve_chunks_fn=retrieve_chunks_fn,
        query_logs_fn=query_logs_fn,
        role_allows_tool_fn=role_allows_tool_fn,
        role_allows_doc_fn=role_allows_doc_fn
    )
    return executors.get_executors()
