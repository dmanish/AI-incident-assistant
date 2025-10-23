"""
scripts/ingest.py
Rebuilds the Chroma vector store from all documents in /data/docs.

Works in:
  1) Docker on local PC/Mac (env comes from .env via docker-compose)
  2) GitHub Codespaces (env from devcontainer/codespaces secrets)

Config (env):
  EMBEDDINGS_PROVIDER = "cpu" (default) | "openai"
  OPENAI_API_KEY      = required if EMBEDDINGS_PROVIDER=openai
  OPENAI_EMBED_MODEL  = (optional) default "text-embedding-3-small"
  CHROMA_DB_DIR       = default ./data/chroma
"""

import os
from pathlib import Path
from typing import List

# Optional .env when running locally outside Docker/Codespaces
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = DATA / "docs"
CHROMA_DIR = Path(os.getenv("CHROMA_DB_DIR", str(DATA / "chroma")))

# Ensure dirs exist
DOCS.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

import chromadb
from chromadb.utils import embedding_functions

COLL_NAME = "security_docs"

def chunks(text: str, size: int = 800, overlap: int = 120):
    toks = text.split()
    i = 0
    while i < len(toks):
        yield " ".join(toks[i:i + size])
        i += max(1, size - overlap)

def get_embedder():
    provider = (os.getenv("EMBEDDINGS_PROVIDER", "cpu") or "cpu").lower()
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
        if not api_key:
            raise ValueError("EMBEDDINGS_PROVIDER=openai but OPENAI_API_KEY is missing.")
        # OpenAI v1-compatible wrapper
        from openai import OpenAI
        class OpenAIv1EmbeddingFunction:
            def __init__(self, api_key: str, model_name: str):
                self.client = OpenAI(api_key=api_key)
                self.model = model_name
            def __call__(self, input: List[str]):
                resp = self.client.embeddings.create(model=self.model, input=input)
                return [d.embedding for d in resp.data]
        print(f"Using OpenAI embeddings ({model}).")
        return OpenAIv1EmbeddingFunction(api_key, model)
    # Default: local CPU
    print("Using local CPU embeddings (all-MiniLM-L6-v2).")
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

def main():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # (Re)create collection with embedder attached (Chroma 0.5.x)
    embed_fn = get_embedder()
    try:
        client.delete_collection(COLL_NAME)  # clean rebuild
    except Exception:
        pass
    coll = client.get_or_create_collection(name=COLL_NAME, embedding_function=embed_fn)

    ids, docs, metas = [], [], []
    files = sorted(DOCS.glob("*.md"))
    if not files:
        print(f"No docs found in {DOCS}")
    for p in files:
        text = p.read_text(encoding="utf-8")
        doc_type = "playbook" if "playbook" in p.name else ("policy" if "policy" in p.name else "kb")
        # SCALAR metadata only
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
        coll.upsert(ids=ids, documents=docs, metadatas=metas)
        print(f"✅ Indexed {len(docs)} chunks from {len(files)} files into Chroma at {CHROMA_DIR}")
    else:
        print("Nothing to index.")

if __name__ == "__main__":
    main()

