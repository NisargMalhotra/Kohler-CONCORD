"""
KOHLER CONCORD — Semantic Response Cache.

Uses sentence-transformer embeddings (via ChromaDB's wrapper) to find
semantically similar previous queries, avoiding redundant LLM calls
for paraphrased questions.  Part of the sustainability / efficiency layer.

Falls back to exact-match hashing if the embedding model cannot load.
"""

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional

import numpy as np

from src.config import settings

logger = logging.getLogger(__name__)

# Lazy import — avoid top-level torchvision errors
_embedding_fn = None
_embedding_available = None  # None = not tried yet


def _get_embedding_fn():
    """Lazy-load the same embedding function used by VectorStore."""
    global _embedding_fn, _embedding_available
    if _embedding_available is not None:
        return _embedding_fn  # may be None if unavailable

    try:
        from chromadb.utils.embedding_functions import (
            SentenceTransformerEmbeddingFunction,
        )
        _embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name=settings.EMBEDDING_MODEL
        )
        _embedding_available = True
        logger.info("Semantic cache: embedding model loaded.")
    except Exception as e:
        logger.warning(f"Semantic cache: embedding model unavailable ({e}), using exact-match.")
        _embedding_fn = None
        _embedding_available = False
    return _embedding_fn


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class ResponseCache:
    """Semantic response cache with configurable similarity threshold.

    Embeds queries using the same model as the vector store and compares
    via cosine similarity. Falls back to SHA-256 exact-match hashing
    when the embedding model is unavailable.
    """

    def __init__(self, ttl: int = None, threshold: float = None):
        self.ttl = ttl if ttl is not None else settings.CACHE_TTL
        self.threshold = (
            threshold if threshold is not None
            else settings.SEMANTIC_CACHE_THRESHOLD
        )
        self._entries: List[Dict[str, Any]] = []

    # ── embedding helpers ────────────────────────────────────────────

    def _embed(self, text: str) -> Optional[np.ndarray]:
        fn = _get_embedding_fn()
        if fn is None:
            return None
        try:
            vecs = fn([text])  # returns List[List[float]]
            return np.array(vecs[0], dtype=np.float32)
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")
            return None

    @staticmethod
    def _hash_key(query: str, persona: str) -> str:
        return hashlib.sha256(f"{persona}:{query.strip().lower()}".encode()).hexdigest()

    # ── public API ───────────────────────────────────────────────────

    def get(self, query: str, persona: str) -> Optional[Dict[str, Any]]:
        """Find a cached response (semantic or exact-match)."""
        # Avoid circular import
        from src.llm import efficiency_stats

        if not self._entries:
            efficiency_stats.cache_misses += 1
            return None

        # Prune expired entries
        now = time.time()
        self._entries = [e for e in self._entries if now - e["timestamp"] <= self.ttl]
        if not self._entries:
            efficiency_stats.cache_misses += 1
            return None

        # Try semantic match first
        query_emb = self._embed(query.strip().lower())
        if query_emb is not None:
            best_score = 0.0
            best_entry = None
            for entry in self._entries:
                if entry["persona"] != persona:
                    continue
                emb = entry.get("embedding")
                if emb is None:
                    continue
                sim = _cosine_similarity(query_emb, emb)
                if sim > best_score:
                    best_score = sim
                    best_entry = entry

            if best_entry is not None and best_score >= self.threshold:
                efficiency_stats.cache_hits += 1
                efficiency_stats.semantic_cache_hits += 1
                efficiency_stats.tokens_saved_by_cache += 2000
                logger.info(
                    f"Semantic cache HIT (sim={best_score:.3f}): "
                    f"'{query[:50]}'"
                )
                return best_entry["response"]

        # Fallback: exact-match hash
        key = self._hash_key(query, persona)
        for entry in self._entries:
            if entry.get("hash") == key:
                efficiency_stats.cache_hits += 1
                efficiency_stats.tokens_saved_by_cache += 2000
                logger.info(f"Exact cache HIT: '{query[:50]}'")
                return entry["response"]

        efficiency_stats.cache_misses += 1
        return None

    def set(self, query: str, persona: str, response: Dict[str, Any]) -> None:
        """Cache a response with its embedding and hash."""
        embedding = self._embed(query.strip().lower())
        self._entries.append({
            "query": query,
            "persona": persona,
            "embedding": embedding,  # may be None
            "hash": self._hash_key(query, persona),
            "response": response,
            "timestamp": time.time(),
        })

    def clear(self) -> None:
        self._entries.clear()

    def stats(self) -> Dict[str, Any]:
        from src.llm import efficiency_stats
        return {
            "total_entries": len(self._entries),
            "hits": efficiency_stats.cache_hits,
            "semantic_hits": efficiency_stats.semantic_cache_hits,
            "misses": efficiency_stats.cache_misses,
            "threshold": self.threshold,
        }
