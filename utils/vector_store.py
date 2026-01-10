import numpy as np
import faiss
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from utils.db import supabase
from utils.config import settings

logger = logging.getLogger(__name__)

class VectorStoreInterface(ABC):
    @abstractmethod
    async def add_vectors(self, user_id: str, vectors: List[List[float]], ids: List[int]):
        pass

    @abstractmethod
    async def search_vectors(self, user_id: str, query_vector: List[float], top_k: int) -> List[Tuple[int, float]]:
        """Returns List of (id, distance)"""
        pass

class FaissStore(VectorStoreInterface):
    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        self.user_indices: Dict[str, faiss.Index] = {}

    def _get_index(self, user_id: str) -> faiss.Index:
        if user_id not in self.user_indices:
            self.user_indices[user_id] = faiss.IndexFlatL2(self.dimension)
        return self.user_indices[user_id]

    async def add_vectors(self, user_id: str, vectors: List[List[float]], ids: List[int]):
        # Note: In FaissStore, 'ids' are currently handled by external MemoryStore mapping
        # since IndexFlatL2 doesn't natively map to DB primary keys easily without IndexIDMap.
        # But for scaling, we keep it simple as it's the 'dev' store.
        index = self._get_index(user_id)
        v_np = np.array(vectors).astype('float32')
        index.add(v_np)

    async def search_vectors(self, user_id: str, query_vector: List[float], top_k: int) -> List[Tuple[int, float]]:
        if user_id not in self.user_indices or self.user_indices[user_id].ntotal == 0:
            return []
        
        index = self.user_indices[user_id]
        v_np = np.array([query_vector]).astype('float32')
        distances, indices = index.search(v_np, top_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1:
                results.append((int(idx), float(dist)))
        return results

class SupabaseVectorStore(VectorStoreInterface):
    """
    Managed vector storage using Supabase pgvector.
    Requires the 'match_memories' RPC function to be defined in PostgreSQL.
    """
    async def add_vectors(self, user_id: str, vectors: List[List[float]], ids: List[int]):
        # Data is already persisted in DB via regular Supabase inserts in MemoryStore
        pass

    async def search_vectors(self, user_id: str, query_vector: List[float], top_k: int) -> List[Tuple[int, float]]:
        try:
            # Call matching function in Supabase
            # match_threshold and match_count are passed to the RPC
            # we use 0.5 as a broad threshold for candidate generation
            response = supabase.rpc('match_memories', {
                'query_embedding': query_vector,
                'match_threshold': 0.5,
                'match_count': top_k,
                'p_user_id': user_id
            }).execute()
            
            # The RPC should return id and similarity/distance
            if not response.data:
                return []
            
            # Convert similarity to distance for consistency with FAISS L2
            # pgvector similarity is usually 1 - distance
            return [(r['id'], 1.0 - r['similarity']) for r in response.data]
        except Exception as e:
            logger.error(f"Supabase vector search failed: {e}")
            return []

def get_vector_store(dimension: int = 1536) -> VectorStoreInterface:
    if settings.VECTOR_STORE_TYPE == "supabase":
        return SupabaseVectorStore()
    return FaissStore(dimension)
