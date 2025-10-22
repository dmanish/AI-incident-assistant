# scripts/bootstrap.py
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
(DOCS := DATA / "docs").mkdir(parents=True, exist_ok=True)
(LOGS := DATA / "logs" / "auth").mkdir(parents=True, exist_ok=True)
(CHROMA := DATA / "chroma").mkdir(parents=True, exist_ok=True)
(POLICY := DATA / "policies").mkdir(parents=True, exist_ok=True)

# 1) Seed minimal docs if missing
policy_md = DOCS / "policies_password.md"
if not policy_md.exists():
    policy_md.write_text("# Password Policy\n- Min 12 chars\n- MFA for admins\n- Rotate every 90 days\n")

playbook_md = DOCS / "playbook_phishing.md"
if not playbook_md.exists():
    playbook_md.write_text("# Phishing Playbook\n1. Isolate device\n2. Notify security\n3. Analyze email\n4. Reset creds\n5. Review\n")

# 2) Seed a small auth log CSV (today) if missing
from datetime import datetime, timezone
today = datetime.now(timezone.utc).date().isoformat()
log_csv = LOGS / f"{today}.csv"
if not log_csv.exists():
    log_csv.write_text(
        "timestamp,user,action,result,ip\n"
        f"{today}T09:15:23Z,jdoe,login,failed,185.21.54.100\n"
        f"{today}T09:17:54Z,jdoe,login,failed,185.21.54.100\n"
        f"{today}T09:18:01Z,admin,login,success,192.168.0.10\n"
    )

# 3) Seed simple RBAC policy if missing
pol_yaml = POLICY / "policies.yaml"
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
        "    allow_docs: [kb]\n"
    )

# 4) Build / refresh Chroma index from docs
import chromadb
from chromadb.utils import embedding_functions

client = chromadb.PersistentClient(path=str(CHROMA))
coll = client.get_or_create_collection("security_docs")

# Simple chunker
def chunks(text, size=800, overlap=120):
    tokens = text.split()
    i = 0
    while i < len(tokens):
        yield " ".join(tokens[i:i+size])
        i += size - overlap

# ...
doc_paths = list(DOCS.glob("*.md"))
if doc_paths:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("OPENAI_API_KEY not set; skipping Chroma embedding/upsert. (Docs seeded, but no index.)")
    else:
        embed_fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=openai_api_key, model_name="text-embedding-3-small"
        )
        ids, docs, meta = [], [], []
        for p in doc_paths:
            text = p.read_text()
            for idx, ch in enumerate(chunks(text)):
                ids.append(f"{p.name}#{idx}")
                docs.append(ch)
                meta.append({
                    "source_path": str(p),
                    "doc_type": "policy" if "policy" in p.name else "playbook",
                })
        if docs:
            # Create collection with embedding function at creation time (more robust)
            coll = client.get_or_create_collection("security_docs", embedding_function=embed_fn)
            coll.upsert(ids=ids, documents=docs, metadatas=meta)
