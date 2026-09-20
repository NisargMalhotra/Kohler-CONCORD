import logging
import os
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from src.config import Document, settings

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, persist_dir: str = None):
        self.persist_dir = persist_dir or settings.CHROMA_DIR
        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.embedding_fn = SentenceTransformerEmbeddingFunction(model_name=settings.EMBEDDING_MODEL)
        self.collection_name = 'kohler_kb'
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn
        )

    def initialize(self, documents: List[Document]) -> None:
        if not documents:
            logger.warning("No documents provided for initialization.")
            return

        ids = []
        texts = []
        metadatas = []
        
        for doc in documents:
            ids.append(doc.metadata.get("chunk_id", str(hash(doc.content))))
            texts.append(doc.content)
            # Ensure flat metadata dict for ChromaDB
            flat_metadata = {k: str(v) if not isinstance(v, (str, int, float, bool)) else v for k, v in doc.metadata.items()}
            metadatas.append(flat_metadata)

        try:
            self.collection.upsert(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
            logger.info(f"Initialized vector store with {len(documents)} documents.")
        except Exception as e:
            logger.error(f"Error initializing vector store: {e}")

    def search(self, query: str, top_k: int = 10, where_filter: dict = None) -> List[Document]:
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_filter
            )
            
            docs = []
            if not results.get("documents") or not results["documents"][0]:
                return docs
                
            for i in range(len(results["documents"][0])):
                content = results["documents"][0][i]
                metadata = results["metadatas"][0][i] if results.get("metadatas") and results["metadatas"][0] else {}
                score = results["distances"][0][i] if results.get("distances") and results["distances"][0] else 0.0
                docs.append(Document(content=content, metadata=metadata, score=score))
                
            return docs
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return []

    def is_initialized(self) -> bool:
        try:
            return self.collection.count() > 0
        except Exception:
            return False

    def get_collection_stats(self) -> dict:
        try:
            count = self.collection.count()
            # Simple summary logic can be added here if needed
            return {"count": count, "metadata_summary": "Available"}
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"count": 0, "error": str(e)}
