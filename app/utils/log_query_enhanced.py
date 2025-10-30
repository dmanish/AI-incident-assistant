# app/utils/log_query_enhanced.py
"""
Enhanced log querying with flexible filtering and date ranges
Extends the original query_failed_logins with more functionality
"""

import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional


def query_authentication_logs_enhanced(
    log_dir: Path,
    duck_db_path: str,
    date_start: str,
    date_end: Optional[str] = None,
    result_filter: str = "failed",
    username: Optional[str] = None,
    ip_address: Optional[str] = None,
    limit: int = 200
) -> pd.DataFrame:
    """
    Enhanced authentication log query with flexible filtering

    Args:
        log_dir: Directory containing CSV log files
        duck_db_path: Path to DuckDB database
        date_start: Start date (ISO format YYYY-MM-DD)
        date_end: End date (ISO format), defaults to date_start
        result_filter: "failed", "successful", or "all"
        username: Optional username filter
        ip_address: Optional IP address filter
        limit: Maximum number of results

    Returns:
        DataFrame with matching log entries
    """
    files = list(log_dir.glob("*.csv"))
    if not files:
        return pd.DataFrame([])

    if date_end is None:
        date_end = date_start

    con = duckdb.connect(duck_db_path, read_only=False)
    try:
        con.execute("PRAGMA threads=2;")
        con.execute("PRAGMA memory_limit='256MB';")

        # Build WHERE clause dynamically
        where_clauses = []
        params = []

        # Date range filter
        where_clauses.append("(cast(timestamp as varchar) >= ? AND cast(timestamp as varchar) <= ?)")
        params.extend([f"{date_start}", f"{date_end} 23:59:59"])

        # Result filter
        if result_filter == "failed":
            where_clauses.append("lower(result) = 'failed'")
        elif result_filter == "successful":
            where_clauses.append("lower(result) = 'successful'")
        # "all" means no filter on result

        # Username filter
        if username:
            where_clauses.append("lower(user) = lower(?)")
            params.append(username)

        # IP address filter
        if ip_address:
            where_clauses.append("ip = ?")
            params.append(ip_address)

        where_clause = " AND ".join(where_clauses)

        sql = f"""
            SELECT timestamp, user, action, result, ip
            FROM read_csv_auto('{(log_dir / "*.csv").as_posix()}', union_by_name=true)
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """
        params.append(limit)

        df = con.execute(sql, params).fetchdf()
        return df

    finally:
        con.close()
