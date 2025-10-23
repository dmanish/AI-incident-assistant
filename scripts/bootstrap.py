# scripts/bootstrap.py
import os
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = DATA / "docs"
LOGS = DATA / "logs" / "auth"
CHROMA_DIR = DATA / "chroma"
POLICY_DIR = DATA / "policies"

DOCS.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
POLICY_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Seed docs / logs / RBAC
# -----------------------------
(policy_md := DOCS / "policies_password.md")
if not policy_md.exists():
    policy_md.write_text(
        "# Password Policy\n"
        "- Min 12 chars\n- MFA for admins\n- Rotate every 90 days\n",
        encoding="utf-8"
    )

(playbook_phish := DOCS / "playbook_phishing.md")
if not playbook_phish.exists():
    playbook_phish.write_text(
        "# Phishing Playbook\n"
        "1. Isolate device\n2. Notify security\n3. Analyze email\n4. Reset creds\n5. Review\n",
        encoding="utf-8"
    )

(playbook_outage := DOCS / "playbook_prod_outage_breach.md")
if not playbook_outage.exists():
    playbook_outage.write_text(
        "# Incident Playbook: Production Outage Caused by Security Breach\n\n"
        "## Severity & Ownership\n"
        "- Severity: SEV-1\n"
        "- Incident Commander (IC): On-call SRE\n"
        "- Security Lead: On-call Security Engineer\n"
        "- Comms Lead: Eng Manager or PR (if external impact)\n\n"
        "## Immediate Actions (T+0–15m)\n"
        "1. IC declares SEV-1 and starts incident bridge (Slack #inc-sev1 + Zoom).\n"
        "2. Security Lead initiates containment: isolate affected hosts, revoke suspected creds/tokens.\n"
        "3. Freeze deploys; enable WAF block rules as needed.\n\n"
        "## Triage (T+15–60m)\n"
        "4. Identify blast radius (services, data, accounts).\n"
        "5. Switch to safe failover if possible; restore minimal service.\n"
        "6. Enable elevated logging; snapshot affected systems for forensics.\n\n"
        "## Escalation Path\n"
        "- IC → Director of Engineering (10 min if unresolved)\n"
        "- Security Lead → Head of Security (immediately on confirmed breach)\n"
        "- If customer data at risk → Legal & Privacy (within 60 min)\n"
        "- If > 1h outage or regulatory impact → Exec Bridge (CEO/CTO)\n\n"
        "## Communication\n"
        "- Internal updates every 15 min on bridge; status page if customer impact > 30 min.\n"
        "- Draft customer comms with Legal/PR once facts are confirmed.\n\n"
        "## Evidence & Forensics\n"
        "- Preserve logs, DB query history, auth events, and disk snapshots.\n"
        "- Do not reboot compromised hosts until snapshots complete.\n\n"
        "## Recovery\n"
        "- Rotate affected secrets/keys; verify integrity before reintroducing nodes.\n"
        "- Post-incident hardening: rules, detections, tabletop.\n\n"
        "## Exit Criteria\n"
        "- Service stable ≥ 1h, containment confirmed, no active threat.\n\n"
        "## Postmortem\n"
        "- Within 72h: blameless write-up, action items with owners & due dates.\n",
        encoding="utf-8"
    )

today = datetime.now(timezone.utc).date().isoformat()
log_csv = LOGS / f"{today}.csv"
if not log_csv.exists():
    log_csv.write_text(
        "timestamp,user,action,result,ip\n"
        f"{today}T09:15:23Z,jdoe,login,failed,185.21.54.100\n"
        f"{today}T09:17:54Z,jdoe,login,failed,185.21.54.100\n"
        f"{today}T09:18:01Z,admin,login,success,192.168.0.10\n",
        encoding="utf-8"
    )

pol_yaml = POLICY_DIR / "policies.yaml"
if not pol_yaml.exists():
    pol_yaml.write_text(
        "roles:\n"
        "  security:\n"
        "    allow_tools: [log_query]\n"
        "    allow_docs: [policy, playbook, kb]\n"
        "  engineering:\n"
        "    allow_tools: [log_query]\n"
        "    allow_docs: [policy, playbook, kb]\n"
        "  sales:\n"
        "    allow_tools: []\n"
        "    allow_docs: [kb]\n",
        encoding="utf-8"
    )

# -----------------------------
# Chroma indexing (configurable embeddings)
# -----------------------------
import chromadb
from chromadb.utils import embedding_functions

def chunks(text: str, size: int = 800, overlap: int = 120):
    toks = text.split()
    i = 0
    while i < len(toks):
        yield " ".join(toks[i:i+size])
        i += max(1, size - overlap)

# Embedding provider selector:
#   EMBEDDINGS_PROVIDER=local (default) | openai
#   OPENAI_API_KEY must be set for openai mode
#   OPENAI_EMBED_MODEL optional (default: text-embedding-3-small)
def get_embedder():
    provider = (os.getenv("EMBEDDINGS_PROVIDER", "local") or "local").lower()
    if provider not in ("local", "openai"):
        provider = "local"

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
        if not api_key:
            print("EMBEDDINGS_PROVIDER=openai but OPENAI_API_KEY missing; falling back to local.")
        else:
            # OpenAI v1-compatible wrapper
            from typing import List
            from openai import OpenAI

            class OpenAIv1EmbeddingFunction:
                def __init__(self, api_key: str, model_name: str):
                    self.client = OpenAI(api_key=api_key)
                    self.model = model_name
                def __call__(self, input: "List[str]") -> "List[List[float]]":
                    resp = self.client.embeddings.create(model=self.model, input=input)
                    return [d.embedding for d in resp.data]

            print(f"Using OpenAI embeddings ({model}).")
            return OpenAIv1EmbeddingFunction(api_key=api_key, model_name=model)

    # Default: local CPU embeddings
    print("Using local CPU embeddings (all-MiniLM-L6-v2).")
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

client = chromadb.PersistentClient(path=str(CHROMA_DIR))

# Reset collection for reproducible demo runs (set CHROMA_RESET=0 to skip)
COLL_NAME = "security_docs"
if os.getenv("CHROMA_RESET", "1") != "0":
    try:
        client.delete_collection(COLL_NAME)
    except Exception:
        pass

embed_fn = get_embedder()

# Attach embedder at collection creation (Chroma 0.5.x)
collection = client.get_or_create_collection(
    name=COLL_NAME,
    embedding_function=embed_fn,
)

ids, docs, metas = [], [], []
for p in sorted(DOCS.glob("*.md")):
    text = p.read_text(encoding="utf-8")
    doc_type = "playbook" if "playbook" in p.name else ("policy" if "policy" in p.name else "kb")
    # SCALAR metadata only (no lists)
    allow_roles_csv = "security,engineering,sales"
    for idx, ch in enumerate(chunks(text)):
        ids.append(f"{p.name}#{idx}")
        docs.append(ch)
        metas.append({
            "source_path": str(p),
            "doc_type": doc_type,
            "allow_roles_csv": allow_roles_csv,
        })

if docs:
    collection.upsert(ids=ids, documents=docs, metadatas=metas)

print("Bootstrap complete: data dirs created, sample docs/logs seeded, Chroma populated.")
