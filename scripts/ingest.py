"""
scripts/ingest.py
-----------------
Rebuilds or refreshes the Chroma vector store from all documents in /data/docs.

Usage:
    python scripts/ingest.py
"""

import os
from pathlib import Path
from chromadb import PersistentClient
from chromadb.utils import embedding_functions

# Directories
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = DATA / "docs"
CHROMA = DATA / "chroma"

# Ensure dirs exist
CHROMA.mkdir(parents=True, exist_ok=True)
DOCS.mkdir(parents=True, exist_ok=True)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize Chroma client
client = PersistentClient(path=str(CHROMA))
collection = client.get_or_create_collection("security_docs")

# Choose embedding model
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY. Set it in .env or Codespaces Secrets.")

embed_fn = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPENAI_API_KEY,
    model_name="text-embedding-3-small",
)

# Simple chunker
def chunks(text: str, size: int = 800, overlap: int = 120):
    tokens = text.split()
    i = 0
    while i < len(tokens):
        yield " ".join(tokens[i:i + size])
        i += size - overlap

# Collect docs
def load_docs():
    for p in DOCS.glob("*.md"):
        yield p.name, p.read_text(), "policy" if "policy" in p.name else "playbook"

def main():
    print("🔄 Rebuilding Chroma index from", DOCS)
    collection.delete(where={})  # clear existing
    ids, docs, meta = [], [], []
    for name, text, doc_type in load_docs():
        for idx, ch in enumerate(chunks(text)):
            ids.append(f"{name}#{idx}")
            docs.append(ch)
            meta.append({
                "source_path": str(DOCS / name),
                "doc_type": doc_type,
                "role_allowed": ["security", "engineering", "sales"],
            })

    collection.upsert(ids=ids, documents=docs, metadatas=meta, embedding_function=embed_fn)
    print(f"✅ Indexed {len(docs)} chunks into Chroma.")

if __name__ == "__main__":
    main()
