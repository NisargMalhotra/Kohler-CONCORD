#!/usr/bin/env python3
"""Build (or rebuild) the customer-facing knowledge base vector index.

Usage:
    python scripts/build_customer_index.py           # build if changed
    python scripts/build_customer_index.py --force   # force rebuild

The index is persisted to ./chroma_customer_db/ and loaded at app
startup without re-indexing.
"""

import hashlib
import os
import sys

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.knowledge_base.loader import KnowledgeBaseLoader
from src.knowledge_base.chunker import DocumentChunker
from src.knowledge_base.customer_store import CustomerVectorStore, CUSTOMER_DATA_DIR

HASH_FILE = os.path.join(PROJECT_ROOT, ".customer_kb_hash")


def _compute_source_hash(data_dir: str) -> str:
    """SHA-256 over the sorted concatenation of every file in data_dir."""
    h = hashlib.sha256()
    if not os.path.isdir(data_dir):
        return ""
    for name in sorted(os.listdir(data_dir)):
        fpath = os.path.join(data_dir, name)
        if os.path.isfile(fpath):
            with open(fpath, "rb") as f:
                h.update(f.read())
    return h.hexdigest()


def main() -> None:
    force = "--force" in sys.argv

    current_hash = _compute_source_hash(CUSTOMER_DATA_DIR)
    if not current_hash:
        print(f"ERROR: No files found in {CUSTOMER_DATA_DIR}")
        sys.exit(1)

    # Check if rebuild is needed
    if not force and os.path.isfile(HASH_FILE):
        with open(HASH_FILE, "r") as f:
            stored = f.read().strip()
        if stored == current_hash:
            print("Customer KB unchanged — skipping rebuild.  Use --force to override.")
            return

    print(f"Loading customer documents from {CUSTOMER_DATA_DIR} ...")
    loader = KnowledgeBaseLoader(data_dir=CUSTOMER_DATA_DIR)
    docs = loader.load_all()
    print(f"  Loaded {len(docs)} raw sections.")

    chunker = DocumentChunker()
    chunks = chunker.chunk_documents(docs)
    print(f"  Chunked into {len(chunks)} pieces.")

    print("Indexing into CustomerVectorStore ...")
    store = CustomerVectorStore()
    store.initialize(chunks)
    stats = store.get_stats()
    print(f"  Done — {stats['count']} vectors stored.")

    # Save hash so we skip next time
    with open(HASH_FILE, "w") as f:
        f.write(current_hash)
    print("Hash saved.  Subsequent app starts will load the pre-built index.")


if __name__ == "__main__":
    main()
