"""
KOHLER CONCORD — Semantic Response Cache.

Uses sentence-transformer embeddings to find semantically similar
previous queries, avoiding redundant LLM calls for paraphrased
questions. Part of the sustainability / efficiency layer.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

from src.config import settings
from src.llm import efficiency_stats

logger = logging.getLogger(__name__)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class ResponseCache:
    """Semantic response cache with configurable similarity threshold.
    
    Instead of exact-match hashing, queries are embedded and compared
    via cosine similarity. A match above the threshold returns the
    cached result, saving all downstream LLM calls.
    """

    def __init__(self, ttl: int = None, threshold: float = None):
        self.ttl = ttl if ttl is not None else settings.CACHE_TTL
        self.threshold = threshold if threshold is not None else settings.SEMANTIC_CACHE_THRESHOLD
        self._entries: List[Dict[str, Any]] = []
        # Lazy-load the embedding model (shared with VectorStore)
        self._model: Optional[SentenceTransformer] = None

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
        return self._model

    def _embed(self, text: str) -> np.ndarray:
        model = self._get_model()
        return model.encode(text, normalize_embeddings=True)

    def get(self, query: str, persona: str) -> Optional[Dict[str, Any]]:
        """Find a semantically similar cached response."""
        if not self._entries:
            efficiency_stats.cache_misses += 1
            return None

        # Prune expired entries first
        now = time.time()
        self._entries = [e for e in self._entries if now - e["timestamp"] <= self.ttl]

        if not self._entries:
            efficiency_stats.cache_misses += 1
            return None

        query_embedding = self._embed(query.strip().lower())

        best_score = 0.0
        best_entry = None

        for entry in self._entries:
            if entry["persona"] != persona:
                continue
            sim = _cosine_similarity(query_embedding, entry["embedding"])
            if sim > best_score:
                best_score = sim
                best_entry = entry

        if best_entry is not None and best_score >= self.threshold:
            efficiency_stats.cache_hits += 1
            efficiency_stats.semantic_cache_hits += 1
            # Estimate tokens saved: a full pipeline run uses ~2000 tokens
            efficiency_stats.tokens_saved_by_cache += 2000
            logger.info(
                f"Semantic cache HIT (sim={best_score:.3f}, "
                f"threshold={self.threshold}): '{query[:50]}'"
            )
            return best_entry["response"]

        efficiency_stats.cache_misses += 1
        return None

    def set(self, query: str, persona: str, response: Dict[str, Any]) -> None:
        """Cache a response with its embedding."""
        embedding = self._embed(query.strip().lower())
        self._entries.append({
            "query": query,
            "persona": persona,
            "embedding": embedding,
            "response": response,
            "timestamp": time.time(),
        })

    def clear(self) -> None:
        self._entries.clear()

    def stats(self) -> Dict[str, Any]:
        return {
            "total_entries": len(self._entries),
            "hits": efficiency_stats.cache_hits,
            "semantic_hits": efficiency_stats.semantic_cache_hits,
            "misses": efficiency_stats.cache_misses,
            "threshold": self.threshold,
        }
