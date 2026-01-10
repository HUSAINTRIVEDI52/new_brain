import sys
import os
import unittest
import asyncio
import numpy as np
import datetime
from unittest.mock import MagicMock, patch, AsyncMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.memory_store import MemoryStore

class TestEnhancedImportance(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = MemoryStore(dimension=4)
        self.user_id = "imp-enhancer-user"
        # Mocking for local tests
        self.store.user_records[self.user_id] = []
        self.store.user_record_maps[self.user_id] = {}
        self.store.user_query_history[self.user_id] = []

    async def test_signal_blending_normalization(self):
        print("\n--- Testing Signal Blending & Normalization ---")
        
        # Create a record with high access but low summary_count and no history
        record = {
            "id": 1, "user_id": self.user_id, "created_at": "2024-01-01T12:00:00Z",
            "access_count": 100, "summary_count": 0, "importance": 1.0,
            "embedding": [0.1, 0.1, 0.1, 0.1]
        }
        
        # Test 1: Just Frequency
        imp_1 = self.store._calculate_effective_importance(record, self.user_id)
        print(f"High Frequency (100) Importance: {imp_1}")
        self.assertLessEqual(imp_1, 1.0)
        self.assertGreater(imp_1, 0.2) # Should have a boost
        
        # Test 2: Add Summary Inclusion
        record["summary_count"] = 10
        imp_2 = self.store._calculate_effective_importance(record, self.user_id)
        print(f"High Frequency + High AI Inclusion Importance: {imp_2}")
        self.assertGreater(imp_2, imp_1)
        
        # Test 3: Add Semantic Reuse (Query History)
        # Push 5 identical query embeddings to history
        self.store.user_query_history[self.user_id] = [np.array([0.1]*4)] * 5
        imp_3 = self.store._calculate_effective_importance(record, self.user_id)
        print(f"High Freq + High AI + High Semantic Reuse Importance: {imp_3}")
        self.assertGreater(imp_3, imp_2)
        self.assertLessEqual(imp_3, 1.0)

    async def test_summary_count_increment(self):
        print("\n--- Testing Summary Count Increment (durability) ---")
        
        record = {
            "id": 505, "user_id": self.user_id, "summary_count": 2,
            "created_at": "2024-01-01T12:00:00Z"
        }
        self.store.user_record_maps[self.user_id] = {505: record}
        
        with patch('utils.memory_store.supabase') as mock_sb:
            # Mock select returning current data
            mock_sb.table().select().in_().eq().execute.return_value = MagicMock(data=[record])
            # Mock update
            mock_sb.table().update().eq().execute.return_value = MagicMock()
            
            await self.store.increment_summary_counts([505], self.user_id)
            
            # Local update check
            self.assertEqual(record["summary_count"], 3)
            print("Verified: Local summary_count incremented")
            
            # DB call check (update called with 3)
            mock_sb.table().update.assert_called_with({"summary_count": 3})
            print("Verified: DB update called with incremented value")

if __name__ == "__main__":
    unittest.main()
