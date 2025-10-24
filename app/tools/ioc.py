# app/tools/ioc.py
import os
import requests

ABUSE_KEY = os.getenv("ABUSEIPDB_KEY")  # optional
IPINFO_KEY = os.getenv("IPINFO_TOKEN")  # optional

DEFAULT_TIMEOUT = 6  # seconds

def enrich_ip(ip: str) -> dict:
    """Return a structured enrichment for an IP address. Works even if no API keys are present (best-effort)."""
    out = {
        "ip": ip,
        "sources": [],
        "score": None,         # AbuseIPDB confidence score (0-100)
        "country": None,
        "asn": None,
        "is_tor": None,
    }

    # AbuseIPDB (reputation)
    try:
        if ABUSE_KEY:
            r = requests.get(
                "https://api.abuseipdb.com/api/v2/check",
                params={"ipAddress": ip, "maxAgeInDays": 90},
                headers={"Key": ABUSE_KEY, "Accept": "application/json"},
                timeout=DEFAULT_TIMEOUT,
            )
            if r.ok:
                data = r.json().get("data", {})
                out["score"] = data.get("abuseConfidenceScore")
                out["is_tor"] = data.get("isTor")
                out["country"] = out.get("country") or data.get("countryCode")
                out["sources"].append("abuseipdb")
            else:
                out["abuseipdb_error"] = f"{r.status_code}"
    except Exception as e:
        out["abuseipdb_error"] = str(e)[:200]

    # ipinfo (ASN/country)
    try:
        if IPINFO_KEY:
            r = requests.get(
                f"https://ipinfo.io/{ip}",
                params={"token": IPINFO_KEY},
                timeout=DEFAULT_TIMEOUT,
            )
            if r.ok:
                data = r.json()
                org = data.get("org") or ""
                out["asn"] = (org.split(" ")[0] if org else None) or out.get("asn")
                out["country"] = out.get("country") or data.get("country")
                out["sources"].append("ipinfo")
            else:
                out["ipinfo_error"] = f"{r.status_code}"
    except Exception as e:
        out["ipinfo_error"] = str(e)[:200]

    return out
