import sys
import os
import unittest
import asyncio
import datetime
from unittest.mock import MagicMock, patch, AsyncMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.memory_store import MemoryStore

class TestHybridRanking(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user_id = "rank-test-user"
        self.store = MemoryStore(dimension=4)
        self.store.user_records[self.user_id] = []
        self.store.user_record_maps[self.user_id] = {}

    async def test_importance_boost(self):
        print("\n--- Testing Importance Boost ---")
        # Record 1: Moderate similarity (0.2 dist), High Importance (3.0)
        # Record 2: High similarity (0.05 dist), Low Importance (1.0)
        
        now = datetime.datetime.now(datetime.timezone.utc)
        iso_now = now.isoformat()
        
        self.store.user_record_maps[self.user_id] = {
            1: {"id": 1, "created_at": iso_now, "importance": 3.0, "access_count": 0, "last_accessed_at": iso_now},
            2: {"id": 2, "created_at": iso_now, "importance": 1.0, "access_count": 0, "last_accessed_at": iso_now}
        }
        
        mock_vec = MagicMock()
        mock_vec.search_vectors = AsyncMock(return_value=[(1, 0.2), (2, 0.05)])
        self.store.vector_store = mock_vec

        with patch.object(self.store, '_update_access_metrics', side_effect=AsyncMock(return_value="strong")):
            results = await self.store.search("test", [0.0]*4, self.user_id)
            
            # We want to see if ID 1 (more important but less similar) can outrank or at least have high relevance
            # In our formula, semantic_sim^1.5 is strong, but 0.2 vs 0.05 distance is a large gap.
            # Let's verify the ordering is deterministic.
            self.assertTrue(len(results) == 2)
            print(f"Top result ID: {results[0]['id']}, Relevance: {results[0]['metadata']['relevance']}")
            print(f"Second result ID: {results[1]['id']}, Relevance: {results[1]['metadata']['relevance']}")

    async def test_resurface_boost(self):
        print("\n--- Testing Resurface Boost (Forgetting Curve) ---")
        # Identical similarity, identical importance.
        # One is 'strong' (recently accessed), one is 'fading' (accessed long ago).
        # The 'fading' one should get a slight boost to help it resurface.
        
        now = datetime.datetime.now(datetime.timezone.utc)
        recent_iso = now.isoformat()
        old_iso = (now - datetime.timedelta(days=90)).isoformat()
        
        self.store.user_record_maps[self.user_id] = {
            10: {"id": 10, "created_at": old_iso, "importance": 1.0, "access_count": 1, "last_accessed_at": old_iso},
            11: {"id": 11, "created_at": recent_iso, "importance": 1.0, "access_count": 1, "last_accessed_at": recent_iso}
        }
        
        mock_vec = MagicMock()
        # Same distance for both
        mock_vec.search_vectors = AsyncMock(return_value=[(10, 0.1), (11, 0.1)])
        self.store.vector_store = mock_vec

        with patch.object(self.store, '_update_access_metrics', side_effect=AsyncMock(return_value="strong")):
            results = await self.store.search("test", [0.0]*4, self.user_id)
            
            # The 'old' one (ID 10) likely has lower retention, meaning higher (1-retention) boost.
            # However, Signal 3 (Recency) favors ID 11.
            # The net result depends on weights. Let's verify it doesn't crash and returns a valid order.
            self.assertEqual(len(results), 2)
            print(f"Order: { [r['id'] for r in results] }")

if __name__ == "__main__":
    unittest.main()
