import logging
from cachetools import LRUCache
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, semantic_limit: int = 500, metadata_limit: int = 5000):
        # Semantic Cache: (user_id, query, top_k) -> QueryResponse data
        self._semantic_cache = LRUCache(maxsize=semantic_limit)
        
        # Metadata Cache: (user_id, memory_id) -> {importance, access_count, last_accessed_at, etc.}
        # CRITICAL: No raw_text stored here.
        self._metadata_cache = LRUCache(maxsize=metadata_limit)

    def get_semantic(self, user_id: str, query: str, top_k: int) -> Optional[List[Dict[str, Any]]]:
        key = (user_id, query, top_k)
        return self._semantic_cache.get(key)

    def set_semantic(self, user_id: str, query: str, top_k: int, results: List[Dict[str, Any]]):
        key = (user_id, query, top_k)
        self._semantic_cache[key] = results

    def invalidate_user_semantic(self, user_id: str):
        """Invalidates all semantic entries for a user."""
        keys_to_remove = [k for k in self._semantic_cache.keys() if k[0] == user_id]
        for k in keys_to_remove:
            self._semantic_cache.pop(k, None)
        logger.debug(f"Invalidated semantic cache for user {user_id}")

    def get_metadata(self, user_id: str, memory_id: int) -> Optional[Dict[str, Any]]:
        key = (user_id, memory_id)
        return self._metadata_cache.get(key)

    def set_metadata(self, user_id: str, memory_id: int, metadata: Dict[str, Any]):
        # Ensure we only store lightweight fields, no raw_text
        safe_metadata = {
            k: v for k, v in metadata.items() 
            if k in ["importance", "access_count", "last_accessed_at", "memory_state", "id", "user_id"]
        }
        key = (user_id, memory_id)
        self._metadata_cache[key] = safe_metadata

    def invalidate_metadata(self, user_id: str, memory_id: int):
        key = (user_id, memory_id)
        self._metadata_cache.pop(key, None)

cache_manager = CacheManager()
