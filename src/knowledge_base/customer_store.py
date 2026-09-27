import logging
import os
from typing import List, Optional

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from src.config import Document, settings

logger = logging.getLogger(__name__)

CUSTOMER_CHROMA_DIR = os.getenv("CUSTOMER_CHROMA_DIR", "./chroma_customer_db")
CUSTOMER_DATA_DIR = os.getenv("CUSTOMER_DATA_DIR", "./data/customer_kb")


class CustomerVectorStore:
    """Isolated vector store for customer-facing knowledge base.
    
    Uses a separate ChromaDB collection and persist directory from the
    internal enterprise KB. Documents are all public — no permission
    filtering is needed.
    """

    def __init__(self, persist_dir: str = None):
        self.persist_dir = persist_dir or CUSTOMER_CHROMA_DIR
        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name=settings.EMBEDDING_MODEL
        )
        self.collection = self.client.get_or_create_collection(
            name="kohler_customer_kb",
            embedding_function=self.embedding_fn,
        )

    def is_ready(self) -> bool:
        """True if the pre-built index has documents."""
        try:
            return self.collection.count() > 0
        except Exception:
            return False

    def initialize(self, documents: List[Document]) -> None:
        """Index documents into the customer collection."""
        if not documents:
            logger.warning("No customer documents provided.")
            return
        ids, texts, metadatas = [], [], []
        for doc in documents:
            ids.append(doc.metadata.get("chunk_id", str(hash(doc.content))))
            texts.append(doc.content)
            flat = {
                k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                for k, v in doc.metadata.items()
            }
            metadatas.append(flat)
        try:
            self.collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
            logger.info(f"Customer KB indexed: {len(documents)} chunks.")
        except Exception as e:
            logger.error(f"Customer KB index error: {e}")

    def search(self, query: str, top_k: int = 8) -> List[Document]:
        """Semantic search — no permission filter needed (all public)."""
        try:
            results = self.collection.query(query_texts=[query], n_results=top_k)
            docs = []
            if not results.get("documents") or not results["documents"][0]:
                return docs
            for i in range(len(results["documents"][0])):
                content = results["documents"][0][i]
                metadata = (
                    results["metadatas"][0][i]
                    if results.get("metadatas") and results["metadatas"][0]
                    else {}
                )
                score = (
                    results["distances"][0][i]
                    if results.get("distances") and results["distances"][0]
                    else 0.0
                )
                docs.append(Document(content=content, metadata=metadata, score=score))
            return docs
        except Exception as e:
            logger.error(f"Customer search error: {e}")
            return []

    def get_stats(self) -> dict:
        try:
            return {"count": self.collection.count()}
        except Exception as e:
            return {"count": 0, "error": str(e)}
