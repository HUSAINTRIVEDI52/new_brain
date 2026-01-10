import sys
import os
import unittest
import asyncio
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.memory_store import MemoryStore

class TestLazyHydration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.dimension = 4
        self.user_id = "lazy-test-user"

    async def test_lazy_loading_trigger(self):
        print("\n--- Testing Lazy Hydration Trigger ---")
        store = MemoryStore(dimension=self.dimension)
        
        # Initially, no users are cached
        self.assertEqual(len(store.user_records), 0)
        print("Verified: Store starts empty (Eager hydration removed)")
        
        # Mock Supabase
        with patch('utils.memory_store.supabase') as mock_sb:
            mock_sb.table().select().eq().execute.return_value = MagicMock(data=[
                {"id": 1, "user_id": self.user_id, "raw_text": "Hi", "embedding": [0.0]*4, "created_at": "2024-01-01T00:00:00Z"}
            ])
            
            # Requesting data for the user should trigger hydration
            await store.get_all_memories(self.user_id)
            
            self.assertIn(self.user_id, store.user_records)
            self.assertEqual(len(store.user_records[self.user_id]), 1)
            print(f"Verified: Hydration triggered for {self.user_id} on first request")

    async def test_lru_eviction(self):
        print("\n--- Testing LRU Eviction ---")
        store = MemoryStore(dimension=self.dimension, max_cached_users=2)
        
        with patch('utils.memory_store.supabase') as mock_sb:
            mock_sb.table().select().eq().execute.return_value = MagicMock(data=[])
            
            # Load User 1, then User 2
            await store._ensure_user_hydrated("user1")
            await store._ensure_user_hydrated("user2")
            self.assertEqual(len(store.user_records), 2)
            
            # Load User 3 -> User 1 should be evicted (as it was loaded first)
            await store._ensure_user_hydrated("user3")
            
            self.assertEqual(len(store.user_records), 2)
            self.assertNotIn("user1", store.user_records)
            self.assertIn("user2", store.user_records)
            self.assertIn("user3", store.user_records)
            print("Verified: LRU eviction removed the least active user")

if __name__ == "__main__":
    unittest.main()
