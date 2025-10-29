# app/agent/agent.py
"""
Minimal Agent:
- decide_tools(user_msg) : uses OpenAI (if available) to choose {rag, logs, both}, else heuristic fallback
- synthesize_answer(...) : assembles prompt with both tool contexts and asks LLM; falls back to local summary
"""

from __future__ import annotations
import os, re
from typing import Dict, Any, Tuple, List, Optional
from openai import OpenAI

def _openai_client() -> Optional[OpenAI]:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    try:
        return OpenAI(api_key=key)
    except Exception:
        return None

def decide_tools(user_msg: str) -> Dict[str, Any]:
    """
    Returns: {"use_rag": bool, "use_logs": bool, "reason": str}
    """
    client = _openai_client()
    if client:
        try:
            sys = (
                "You route enterprise security questions to tools.\n"
                "- Use RAG for policies/process/playbooks/how/what.\n"
                "- Use LOGS for real-time evidence: today/last N days, failed login(s), attempts, counts, which IP/user.\n"
                "Respond as compact JSON: {\"use_rag\":true|false, \"use_logs\":true|false, \"reason\":\"...\"}."
            )
            msg = [{"role":"system","content":sys},{"role":"user","content":user_msg}]
            r = client.chat.completions.create(
                model=os.getenv("OPENAI_ROUTER_MODEL","gpt-4o-mini"),
                messages=msg,
                temperature=0,
                max_tokens=120
            )
            import json
            txt = r.choices[0].message.content.strip()
            data = json.loads(txt)
            return {
                "use_rag": bool(data.get("use_rag", False)),
                "use_logs": bool(data.get("use_logs", False)),
                "reason": str(data.get("reason","")).strip()[:200]
            }
        except Exception:
            pass

    # Fallback heuristic
    t = user_msg.lower()

    # Log query signals: any mention of login events, time ranges, or specific users/IPs
    logs_signals = any(s in t for s in [
        "login", "logout", "auth", "attempt",  # Auth events
        "today", "yesterday", "this week", "last week", "this month",  # Time ranges
        "past ", "last ", "recent",  # Relative time
        "show logs", "query logs", "check logs",  # Explicit log requests
        "how many", "count", "number of"  # Quantitative queries (usually need logs)
    ])

    # Policy/procedure signals: asking for guidance, not data
    policy_signals = any(s in t for s in [
        "policy", "playbook", "procedure", "process",
        "should i", "what should", "how do i", "how to handle",
        "how to respond", "how to escalate", "what to do",
        "steps for", "guidance"
    ])

    # If it's clearly a logs query, only use RAG if policy/playbook is explicitly mentioned
    if logs_signals and not policy_signals:
        return {
            "use_rag": False,
            "use_logs": True,
            "reason": "heuristic:logs-only"
        }

    # If both signals, use both tools
    if logs_signals and policy_signals:
        return {
            "use_rag": True,
            "use_logs": True,
            "reason": "heuristic:logs+rag"
        }

    # Otherwise, default to RAG for policy/procedure questions
    return {
        "use_rag": True,
        "use_logs": False,
        "reason": "heuristic:rag-only"
    }

def synthesize_answer(
    user_msg: str,
    rag_context: str,
    logs_context: str
) -> str:
    """
    Prefer OpenAI; fallback to local stitching.
    """
    client = _openai_client()
    if not client:
        # Local fallback
        out = "Here’s a concise answer based on available context.\n"
        if rag_context:
            out += "\nPolicy/Playbook context:\n" + rag_context[:1200]
        if logs_context:
            out += "\nLog evidence:\n" + logs_context[:600]
        return out

    sys = (
        "You are an enterprise security incident assistant.\n"
        "Use policy/playbook excerpts from `Policy Context` and log summaries from `Log Evidence`.\n"
        "Be concise and actionable. If log evidence is empty, say what to check next rather than guessing."
    )
    prompt = (
        f"User Query:\n{user_msg}\n\n"
        f"Policy Context:\n{rag_context or '(none)'}\n\n"
        f"Log Evidence:\n{logs_context or '(none)'}\n"
    )
    r = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),
        messages=[{"role":"system","content":sys},{"role":"user","content":prompt}],
        temperature=0.2,
        max_tokens=600
    )
    return r.choices[0].message.content

