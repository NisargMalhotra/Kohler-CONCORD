import hashlib
import time
import logging
from typing import Optional, Dict, Any

from src.config import settings
from src.llm import efficiency_stats

logger = logging.getLogger(__name__)

class ResponseCache:
    """In-memory cache with TTL to improve sustainability."""
    
    _store: Dict[str, Dict[str, Any]] = {}

    def __init__(self, ttl: int = None):
        self.ttl = ttl if ttl is not None else settings.CACHE_TTL

    def _make_key(self, query: str, persona: str) -> str:
        key_str = f"{query.strip().lower()}||{persona}"
        return hashlib.sha256(key_str.encode("utf-8")).hexdigest()

    def get(self, query: str, persona: str) -> Optional[Dict[str, Any]]:
        """Retrieve a cached response if valid."""
        key = self._make_key(query, persona)
        entry = self._store.get(key)
        
        if entry:
            if self._is_expired(entry):
                del self._store[key]
                efficiency_stats.cache_misses += 1
                return None
                
            efficiency_stats.cache_hits += 1
            efficiency_stats.tokens_saved_by_cache += 300 
            return entry["response"]
            
        efficiency_stats.cache_misses += 1
        return None

    def set(self, query: str, persona: str, response: Dict[str, Any]) -> None:
        """Cache a response."""
        key = self._make_key(query, persona)
        self._store[key] = {
            "timestamp": time.time(),
            "response": response
        }

    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        return time.time() - entry["timestamp"] > self.ttl

    def clear(self) -> None:
        """Clear the cache entirely."""
        self._store.clear()

    def stats(self) -> Dict[str, int]:
        return {
            "hits": efficiency_stats.cache_hits,
            "misses": efficiency_stats.cache_misses,
            "size": len(self._store)
        }
