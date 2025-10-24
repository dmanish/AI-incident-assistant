# app/tools/cve.py
import re
import requests

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
CISA_KEV = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

DEFAULT_TIMEOUT = 6  # seconds
_CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.I)

def find_cves(text: str):
    return _CVE_RE.findall(text or "")

def cve_lookup(cve_id: str) -> dict:
    sev = None
    summary = None

    # NVD: summary + severity (best effort)
    try:
        r = requests.get(NVD_API, params={"cveId": cve_id}, timeout=DEFAULT_TIMEOUT)
        if r.ok and r.json().get("vulnerabilities"):
            item = r.json()["vulnerabilities"][0]["cve"]
            descs = item.get("descriptions") or []
            summary = (descs[0].get("value") if descs else None) or summary
            metrics = item.get("metrics") or {}
            for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                if metrics.get(key):
                    sev = metrics[key][0]["cvssData"].get("baseSeverity")
                    break
    except Exception:
        pass

    kev = False
    # CISA KEV: is it known exploited?
    try:
        kev_json = requests.get(CISA_KEV, timeout=DEFAULT_TIMEOUT).json()
        kev = any(
            (e.get("cveID") or "").upper() == cve_id.upper()
            for e in kev_json.get("vulnerabilities", [])
        )
    except Exception:
        pass

    return {"cve": cve_id, "severity": sev, "summary": summary, "kev": kev}
