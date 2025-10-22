# scripts/bootstrap.py
import os
from pathlib import Path
from datetime import datetime, timezone

# ----------------------------
# Paths & dirs
# ----------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = DATA / "docs"
LOGS = DATA / "logs" / "auth"
CHROMA = DATA / "chroma"
POLICY = DATA / "policies"

for d in (DOCS, LOGS, CHROMA, POLICY):
    d.mkdir(parents=True, exist_ok=True)

# ----------------------------
# 1) Seed minimal docs if missing
# ----------------------------
policy_md = DOCS / "policies_password.md"
if not policy_md.exists():
    policy_md.write_text(
        "# Password Policy\n"
        "- Min 12 chars\n"
        "- MFA for admins\n"
        "- Rotate every 90 days\n"
    )

playbook_md = DOCS / "playbook_phishing.md"
if not playbook_md.exists():
    playbook_md.write_text(
        "# Phishing Playbook\n"
        "1. Isolate device\n"
        "2. Notify security\n"
        "3. Analyze email\n"
        "4. Reset creds\n"
        "5. Review\n"
    )

# ----------------------------
# 2) Seed a small auth log CSV (today) if missing
# ----------------------------
today = datetime.now(timezone.utc).date().isoformat()
log_csv = LOGS / f"{today}.csv"
if not log_csv.exists():
    log_csv.write_text(
        "timestamp,user,action,result,ip\n"
        f"{today}T09:15:23Z,jdoe,login,failed,185.21.54.100\n"
        f"{today}T09:17:54Z,jdoe,login,failed,185.21.54.100\n"
        f"{today}T09:18:01Z,admin,login,success,192.168.0.10\n"
    )

# ----------------------------
# 3) Seed simple RBAC policy if missing
# ----------------------------
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

# ----------------------------
# 4) Build / refresh Chroma index from docs
#    - Prefer OpenAI embeddings when available
#    - Fallback to local SentenceTransformer CPU model if missing/quota-limited
#    - Drop & recreate collection to avoid partial state
# ----------------------------
import chromadb
from chromadb import PersistentClient
from chromadb.utils import embedding_functions

client = PersistentClient(path=str(CHROMA))

def chunks(text: str, size: int = 800, overlap: int = 120):
    tokens = text.split()
    i = 0
    step = max(size - overlap, 1)
    while i < len(tokens):
        yield " ".join(tokens[i:i + size])
        i += step

doc_paths = list(DOCS.glob("*.md"))
if not doc_paths:
    print("No docs found to index. Bootstrap complete.")
    raise SystemExit(0)

ids, docs, meta = [], [], []
for p in doc_paths:
    text = p.read_text()
    doc_type = "policy" if "policy" in p.name else "playbook"
    for idx, ch in enumerate(chunks(text)):
        ids.append(f"{p.name}#{idx}")
        docs.append(ch)
        meta.append({
            "source_path": str(p),
            "doc_type": doc_type,
            "role_allowed": ["security", "engineering", "sales"],
        })

def use_openai_embedder():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing")
    return embedding_functions.OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name="text-embedding-3-small",
    )

def use_local_embedder():
    # ~90MB download on first run; cached afterwards
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    class STWrapper:
        def __call__(self, input):
            vecs = model.encode(input, convert_to_numpy=True, normalize_embeddings=True).tolist()
            return vecs
    return STWrapper()

def rebuild_with_embedder(embed_fn, label="openai"):
    # Drop existing collection (if any) to ensure a clean rebuild
    try:
        client.delete_collection("security_docs")
    except Exception:
        pass  # ok if it doesn't exist
    coll = client.get_or_create_collection("security_docs", embedding_function=embed_fn)
    coll.upsert(ids=ids, documents=docs, metadatas=meta)
    return coll, label

embedder_used = None
collection = None

try:
    embed_fn = use_openai_embedder()
    print("Using OpenAI embeddings (text-embedding-3-small).")
    collection, embedder_used = rebuild_with_embedder(embed_fn, "openai")
except Exception as e:
    print(f"OpenAI embeddings unavailable: {e}\nFalling back to local CPU embeddings (all-MiniLM-L6-v2).")
    try:
        embed_fn_local = use_local_embedder()
        collection, embedder_used = rebuild_with_embedder(embed_fn_local, "local")
    except Exception as e2:
        print(f"Local embedding failed: {e2}")
        print("Proceeding without embeddings (documents seeded but no vectors).")
        # Ensure an empty collection exists (no embedder bound)
        try:
            client.delete_collection("security_docs")
        except Exception:
            pass
        collection = client.get_or_create_collection("security_docs")
        embedder_used = None

print(f"Bootstrap complete: data dirs created, sample docs/logs seeded, Chroma populated. Embedder={embedder_used}")
