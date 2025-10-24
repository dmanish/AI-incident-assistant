# app/security/dlp.py
"""
Post-LLM masking (DLP) for sensitive outputs.
- Fast regex detectors (emails, IPv4/IPv6, JWT-like, UUID, AWS AKIA, generic secrets)
- Entropy-based secret detection for high-entropy tokens
- Keyword redaction (from env or default)
- Role-aware hook (currently not revealing; future: reveal-once)
"""

from __future__ import annotations
import os
import re
import math
from typing import Dict, Tuple, List

# ---------- Patterns ----------
EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+\-]+)@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b")
IPV4_RE = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.|$)){4}\b")
# Lightweight IPv6 (not exhaustive, but practical)
IPV6_RE = re.compile(r"\b(?:[A-Fa-f0-9]{1,4}:){2,7}[A-Fa-f0-9]{1,4}\b")

# JWT-like (base64url header.payload.signature)
JWT_RE = re.compile(r"\beyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\b")

UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}\b")

AWS_AKID_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")

# Generic “secretish” token: long, URL-safe chars
GENERIC_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_\-]{24,}\b")

# Safe allowlist patterns (never mask)
CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)

# Optional keyword redaction list (comma-separated)
KEYWORD_LIST = [k.strip() for k in os.getenv("DLP_KEYWORDS", "").split(",") if k.strip()]

ENTROPY_THRESHOLD = float(os.getenv("DLP_ENTROPY_THRESHOLD", "3.2"))

def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    length = len(s)
    return -sum((c/length) * math.log2(c/length) for c in freq.values())

def _mask_email(m: re.Match) -> str:
    user, domain = m.group(1), m.group(2)
    if len(user) > 2:
        u = user[0] + "***" + user[-1]
    else:
        u = user[0] + "***"
    # mask domain label parts
    parts = domain.split(".")
    parts = [p[0] + "***" if p else p for p in parts]
    return f"{u}@{'.'.join(parts)}"

def _mask_ipv4(m: re.Match) -> str:
    # Keep /24 only
    octets = m.group(0).split(".")
    return f"{octets[0]}.{octets[1]}.{octets[2]}.*"

def _mask_ipv6(m: re.Match) -> str:
    # Collapse middle
    return m.group(0).split(":")[0] + ":****:****::/64"

def _mask_token(_: re.Match) -> str:
    return "[REDACTED]"

def _mask_uuid(_: re.Match) -> str:
    return "[UUID]"

def _mask_akia(_: re.Match) -> str:
    return "[AWS_ACCESS_KEY_ID]"

def _mask_keyword(text: str) -> Tuple[str, int]:
    count = 0
    out = text
    for kw in KEYWORD_LIST:
        # whole-word-ish replace; case-insensitive
        pat = re.compile(rf"(?i)(?<!\w){re.escape(kw)}(?!\w)")
        out, n = pat.subn("[REDACTED]", out)
        count += n
    return out, count

def _mask_entropy_tokens(text: str) -> Tuple[str, int]:
    # Mask generic tokens above entropy threshold unless on allowlist (like CVE)
    count = 0
    def repl(m: re.Match) -> str:
        token = m.group(0)
        if CVE_RE.search(token):  # never mask CVE ids
            return token
        if _shannon_entropy(token) >= ENTROPY_THRESHOLD:
            nonlocal count
            count += 1
            return "[REDACTED]"
        return token
    out = GENERIC_TOKEN_RE.sub(repl, text)
    return out, count

def mask_text(text: str, role: str = "unknown") -> Tuple[str, Dict[str, int]]:
    """
    Returns masked_text and summary counts by entity type.
    Role hook is reserved for future “reveal-once” or reduced masking.
    """
    counts = {
        "email": 0, "ipv4": 0, "ipv6": 0, "jwt": 0,
        "uuid": 0, "aws_key": 0, "generic_secret": 0, "keywords": 0
    }
    out = text

    # Keyword masking
    if KEYWORD_LIST:
        out, n = _mask_keyword(out)
        counts["keywords"] += n

    # Structured patterns
    out, n = EMAIL_RE.subn(_mask_email, out)
    counts["email"] += n

    out, n = IPV4_RE.subn(_mask_ipv4, out)
    counts["ipv4"] += n

    out, n = IPV6_RE.subn(_mask_ipv6, out)
    counts["ipv6"] += n

    out, n = JWT_RE.subn(_mask_token, out)
    counts["jwt"] += n

    out, n = UUID_RE.subn(_mask_uuid, out)
    counts["uuid"] += n

    out, n = AWS_AKID_RE.subn(_mask_akia, out)
    counts["aws_key"] += n

    # Entropy-based last
    out, n = _mask_entropy_tokens(out)
    counts["generic_secret"] += n

    return out, counts

