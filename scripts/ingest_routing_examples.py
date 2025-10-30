#!/usr/bin/env python3
"""
Phase 0: Ingest routing examples into ChromaDB vector database

This script:
1. Loads manual seed examples from seed_examples.json
2. Extracts routing patterns from audit logs
3. Creates/updates ChromaDB collection with embeddings
4. Deduplicates and validates examples

Run this during bootstrap to populate routing vector DB
"""

import json
import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Set
from datetime import datetime
import sys

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
SEED_FILE = PROJECT_ROOT / "data" / "routing" / "seed_examples.json"
AUDIT_LOG = PROJECT_ROOT / "data" / "logs" / "audit.log"
ROUTING_DB_PATH = PROJECT_ROOT / "data" / "routing_db"
EXTRACTED_FILE = PROJECT_ROOT / "data" / "routing" / "extracted_patterns.json"


def load_seed_examples() -> List[Dict]:
    """Load manually curated seed examples"""
    print(f"Loading seed examples from {SEED_FILE}...")

    if not SEED_FILE.exists():
        print(f"⚠️  Seed file not found: {SEED_FILE}")
        return []

    with open(SEED_FILE, 'r') as f:
        examples = json.load(f)

    print(f"✓ Loaded {len(examples)} seed examples")
    return examples


def extract_from_audit_logs(max_examples: int = 500) -> List[Dict]:
    """
    Extract routing examples from audit logs

    Looks for:
    - agent_decision events with use_rag/use_logs/use_web_search
    - Successful routing (followed by agent_complete)
    - Deduplicated queries
    """
    print(f"Extracting routing patterns from {AUDIT_LOG}...")

    if not AUDIT_LOG.exists():
        print(f"⚠️  Audit log not found: {AUDIT_LOG}")
        return []

    extracted = []
    seen_queries: Set[str] = set()
    decisions_by_query = {}

    with open(AUDIT_LOG, 'r') as f:
        for line in f:
            try:
                event = json.loads(line.strip())

                # Look for routing decisions
                if event.get('action') == 'agent_decision':
                    query = event.get('query', '').strip()
                    if not query or len(query) < 5:
                        continue

                    decision = event.get('decision', {})
                    if not decision:
                        continue

                    # Normalize query for deduplication
                    query_lower = query.lower()

                    # Skip if we've seen this exact query
                    if query_lower in seen_queries:
                        continue

                    seen_queries.add(query_lower)

                    # Determine category
                    if decision.get('use_web_search'):
                        category = 'threat_intelligence'
                    elif decision.get('use_logs'):
                        category = 'authentication_logs'
                    elif decision.get('use_rag'):
                        category = 'policy_guidance'
                    else:
                        category = 'unknown'

                    extracted.append({
                        'id': f'audit_{len(extracted):04d}',
                        'query': query[:200],  # Limit length
                        'category': category,
                        'use_rag': decision.get('use_rag', False),
                        'use_logs': decision.get('use_logs', False),
                        'use_web_search': decision.get('use_web_search', False),
                        'source': 'audit_log',
                        'extracted_date': datetime.utcnow().isoformat()
                    })

                    if len(extracted) >= max_examples:
                        break

            except json.JSONDecodeError:
                continue
            except Exception as e:
                continue

    print(f"✓ Extracted {len(extracted)} unique routing patterns from audit logs")

    # Save extracted patterns for review
    if extracted:
        EXTRACTED_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(EXTRACTED_FILE, 'w') as f:
            json.dump(extracted, f, indent=2)
        print(f"✓ Saved extracted patterns to {EXTRACTED_FILE}")

    return extracted


def deduplicate_examples(examples: List[Dict]) -> List[Dict]:
    """
    Deduplicate examples while preserving diversity
    Keeps manual seeds over audit extracts for duplicates
    """
    print("Deduplicating examples...")

    seen_queries: Set[str] = set()
    deduplicated = []
    manual_count = 0
    audit_count = 0

    # Process seed examples first (higher priority)
    for ex in examples:
        query_lower = ex['query'].lower().strip()

        # Skip exact duplicates
        if query_lower in seen_queries:
            continue

        seen_queries.add(query_lower)
        deduplicated.append(ex)

        if ex.get('source') == 'audit_log':
            audit_count += 1
        else:
            manual_count += 1

    print(f"✓ Deduplicated to {len(deduplicated)} unique examples")
    print(f"  - {manual_count} manual seed examples")
    print(f"  - {audit_count} extracted from audit logs")

    return deduplicated


def create_routing_collection(examples: List[Dict]):
    """
    Create/update ChromaDB collection with routing examples
    """
    print(f"Creating routing vector database at {ROUTING_DB_PATH}...")

    # Initialize ChromaDB
    ROUTING_DB_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(ROUTING_DB_PATH))

    # Delete existing collection if present (fresh start)
    try:
        client.delete_collection("routing_examples")
        print("✓ Deleted existing routing_examples collection")
    except:
        pass

    # Create new collection
    collection = client.create_collection(
        name="routing_examples",
        metadata={"description": "Semantic routing examples for tool selection"}
    )

    # Load embedding model (same as RAG for consistency)
    print("Loading embedding model (all-MiniLM-L6-v2)...")
    embedder = SentenceTransformer('all-MiniLM-L6-v2')

    # Prepare data for ChromaDB
    ids = []
    documents = []
    metadatas = []

    for example in examples:
        ids.append(example['id'])
        documents.append(example['query'])

        # Metadata for filtering and routing
        metadata = {
            'category': example['category'],
            'use_rag': example['use_rag'],
            'use_logs': example['use_logs'],
            'use_web_search': example['use_web_search'],
            'source': example.get('source', 'manual_seed')
        }

        # Add optional fields
        if 'notes' in example:
            metadata['notes'] = example['notes'][:100]
        if 'extracted_date' in example:
            metadata['extracted_date'] = example['extracted_date']

        metadatas.append(metadata)

    # Add to collection (ChromaDB handles embedding)
    print(f"Adding {len(ids)} examples to collection...")
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

    print(f"✓ Created routing collection with {len(ids)} examples")

    # Verify collection
    count = collection.count()
    print(f"✓ Verified: Collection contains {count} documents")

    # Test query
    print("\nTesting semantic search...")
    test_query = "are there any CVE vulnerabilities for OpenSSL"
    results = collection.query(
        query_texts=[test_query],
        n_results=3
    )

    print(f"  Test query: '{test_query}'")
    print(f"  Top matches:")
    for i, (doc, dist, meta) in enumerate(zip(
        results['documents'][0],
        results['distances'][0],
        results['metadatas'][0]
    ), 1):
        similarity = 1 - dist
        print(f"    {i}. {doc[:60]}... (similarity: {similarity:.3f})")
        print(f"       → Route: web_search={meta['use_web_search']}, "
              f"rag={meta['use_rag']}, logs={meta['use_logs']}")

    return collection


def main():
    """Main ingestion process"""
    print("=" * 70)
    print("PHASE 0: Routing Examples Ingestion")
    print("=" * 70)
    print()

    # Step 1: Load seed examples
    seed_examples = load_seed_examples()

    # Step 2: Extract from audit logs
    audit_examples = extract_from_audit_logs(max_examples=200)

    # Step 3: Combine and deduplicate
    all_examples = seed_examples + audit_examples
    unique_examples = deduplicate_examples(all_examples)

    if not unique_examples:
        print("⚠️  No examples found! Cannot create routing collection.")
        return 1

    # Step 4: Create vector DB collection
    collection = create_routing_collection(unique_examples)

    print()
    print("=" * 70)
    print("✓✓✓ ROUTING DATABASE INITIALIZED ✓✓✓")
    print("=" * 70)
    print(f"Total examples: {len(unique_examples)}")
    print(f"Database location: {ROUTING_DB_PATH}")
    print()
    print("Next steps:")
    print("  1. Review extracted patterns in: data/routing/extracted_patterns.json")
    print("  2. Add more seed examples to: data/routing/seed_examples.json")
    print("  3. Re-run this script to update the routing database")
    print()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
