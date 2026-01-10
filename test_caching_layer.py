import sys
import os
import unittest
import asyncio
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.cache import cache_manager
from utils.memory_store import MemoryStore

class TestCachingLayer(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user_id = "cache-user"
        self.memory_id = 123
        # Clear caches before each test
        cache_manager.invalidate_user_semantic(self.user_id)
        cache_manager.invalidate_metadata(self.user_id, self.memory_id)

    def test_metadata_isolation(self):
        print("\n--- Testing Metadata Isolation (No Raw Text) ---")
        full_record = {
            "id": self.memory_id,
            "user_id": self.user_id,
            "raw_text": "Sensitive content that should not be in metadata cache",
            "importance": 0.8,
            "access_count": 5
        }
        
        cache_manager.set_metadata(self.user_id, self.memory_id, full_record)
        cached = cache_manager.get_metadata(self.user_id, self.memory_id)
        
        self.assertIsNotNone(cached)
        self.assertIn("importance", cached)
        self.assertNotIn("raw_text", cached)
        print("Verified: Metadata cache excludes raw_text")

    async def test_semantic_invalidation_on_upload(self):
        print("\n--- Testing Semantic Invalidation on Upload ---")
        store = MemoryStore(dimension=4)
        
        # 1. Mock a hydrated user
        store.user_records[self.user_id] = []
        store.user_record_maps[self.user_id] = {}
        
        # 2. Prime semantic cache
        cache_manager.set_semantic(self.user_id, "test query", 5, [{"id": 1}])
        self.assertIsNotNone(cache_manager.get_semantic(self.user_id, "test query", 5))
        
        # 3. Add a memory (should invalidate semantic cache)
        with patch('utils.memory_store.supabase') as mock_sb:
            mock_sb.table().insert().execute.return_value = MagicMock(data=[{"id": 101, "raw_text": "new", "created_at": "2024-01-01"}])
            
            with patch.object(store.vector_store, 'add_vectors', new_callable=MagicMock) as mock_add_vec:
                # Need to return an awaitable for async mock
                future = asyncio.Future()
                future.set_result(None)
                mock_add_vec.return_value = future

                await store.add_memory("new note", self.user_id, "sum", [0.0]*4)
                
                # Verify semantic cache is gone
                self.assertIsNone(cache_manager.get_semantic(self.user_id, "test query", 5))
                print("Verified: Semantic cache invalidated after adding memory")

if __name__ == "__main__":
    unittest.main()
