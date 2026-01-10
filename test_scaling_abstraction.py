import sys
import os
import unittest
import asyncio
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.memory_store import MemoryStore
from utils.vector_store import FaissStore, SupabaseVectorStore

class TestScalingAbstraction(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # We use a custom dimension for testing
        self.dimension = 4
        self.user_id = "test-user-scaling"

    async def test_store_switching(self):
        print("\n--- Testing VectorStore Switching ---")
        
        # 1. Test FAISS default
        with patch('utils.config.settings.VECTOR_STORE_TYPE', 'faiss'):
            from utils.vector_store import get_vector_store
            store = get_vector_store(self.dimension)
            self.assertIsInstance(store, FaissStore)
            print("Verified: FAISS store selected by default")

        # 2. Test Supabase switch
        with patch('utils.config.settings.VECTOR_STORE_TYPE', 'supabase'):
            store = get_vector_store(self.dimension)
            self.assertIsInstance(store, SupabaseVectorStore)
            print("Verified: Supabase store selected via config")

    @patch('utils.memory_store.supabase')
    async def test_stateless_resolution(self, mock_supabase):
        print("\n--- Testing Stateless Record Resolution ---")
        # Initialize MemoryStore
        store = MemoryStore(dimension=self.dimension)
        
        # Mock search results returning an ID NOT in local cache
        mock_vec_store = MagicMock()
        async def mock_search(*args, **kwargs):
            return [(999, 0.1)]
        mock_vec_store.search_vectors = mock_search
        store.vector_store = mock_vec_store
        
        # Mock Supabase returning the missing record
        mock_supabase.table().select().eq().execute.return_value = MagicMock(data=[{
            "id": 999,
            "user_id": self.user_id,
            "raw_text": "Stateless Memory",
            "created_at": "2024-01-01T00:00:00Z",
            "importance": 1.0,
            "access_count": 0
        }])
        
        # Perform search as if it's a new server instance
        results = await store.search("query", [0.0]*self.dimension, self.user_id)
        
        print(f"Search result ID: {results[0]['id']}")
        self.assertEqual(results[0]["id"], 999)
        self.assertEqual(results[0]["raw_text"], "Stateless Memory")
        print("Verified: Missing records are resolved from DB (Stateless ready)")

if __name__ == "__main__":
    unittest.main()
