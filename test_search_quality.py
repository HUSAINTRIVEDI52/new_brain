import sys
import os
import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.memory_store import MemoryStore
from utils.ai import AIClient

class TestSearchQuality(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user_id = "search-quality-user"
        self.store = MemoryStore(dimension=4)
        # Manually hydrate for test
        self.store.user_records[self.user_id] = []
        self.store.user_record_maps[self.user_id] = {}

    def test_semantic_thresholding(self):
        print("\n--- Testing Semantic Thresholding (Noise Reduction) ---")
        # Mock vector search returning one strong match (0.1) and one weak match (0.6)
        # The threshold is 0.45, so the 0.6 should be filtered out.
        
        # Prime maps
        iso_now = "2024-01-01T12:00:00Z"
        self.store.user_record_maps[self.user_id] = {
            1: {"id": 1, "created_at": iso_now, "importance": 1.0, "access_count": 0, "last_accessed_at": iso_now},
            2: {"id": 2, "created_at": iso_now, "importance": 1.0, "access_count": 0, "last_accessed_at": iso_now}
        }
        
        mock_vec = MagicMock()
        async def mock_search(*args): return [(1, 0.1), (2, 0.6)]
        mock_vec.search_vectors = mock_search
        self.store.vector_store = mock_vec
        
        # Run search
        with patch.object(self.store, '_update_access_metrics', new_callable=MagicMock) as mock_metrics:
             mock_metrics.side_effect = AsyncMock(return_value="strong")
             
             loop = asyncio.get_event_loop()
             results = loop.run_until_complete(self.store.search("test", [0.0]*4, self.user_id))
             
             self.assertEqual(len(results), 1)
             self.assertEqual(results[0]["id"], 1)
             print("Verified: Weak match (0.6 distance) filtered by threshold")

    async def test_temporal_intent_boost(self):
        print("\n--- Testing Temporal Intent Boost ---")
        # Two identical matches (same distance), but one is newer.
        # "recent" query should favor the newer one more strongly.
        
        now_dt = "2024-01-10T18:00:00Z"
        old_dt = "2023-01-01T18:00:00Z"
        
        self.store.user_record_maps[self.user_id] = {
            10: {"id": 10, "created_at": old_dt, "importance": 1.0, "access_count": 0, "last_accessed_at": old_dt},
            11: {"id": 11, "created_at": now_dt, "importance": 1.0, "access_count": 0, "last_accessed_at": now_dt}
        }
        
        mock_vec = MagicMock()
        mock_vec.search_vectors = AsyncMock(return_value=[(10, 0.1), (11, 0.1)])
        self.store.vector_store = mock_vec

        with patch.object(self.store, '_update_access_metrics', new_callable=MagicMock) as mock_metrics:
            mock_metrics.side_effect = AsyncMock(return_value="strong")
            # Standard search
            res1 = await self.store.search("routine search", [0.0]*4, self.user_id)
            
            # Temporal search
            res2 = await self.store.search("recent thoughts", [0.0]*4, self.user_id)
            
            # Since internal scores are lower = better, and we sort by them:
            # We expect result 11 (newest) to be at index 0
            self.assertEqual(res2[0]["id"], 11)
            print("Verified: Temporal query correctly prioritized newest content")

if __name__ == "__main__":
    unittest.main()
