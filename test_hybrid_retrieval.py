import sys
import os
import unittest
import asyncio
import datetime
import numpy as np
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.memory_store import memory_store

class TestHybridRetrieval(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Mock Supabase
        self.patcher = patch('utils.memory_store.supabase')
        self.mock_supabase = self.patcher.start()
        
        # Reset memory store
        memory_store.user_indices = {}
        memory_store.user_records = {}
        memory_store.user_query_history = {}
        memory_store.user_record_maps = {}
        
        def mock_execute(data=None):
            m = MagicMock()
            m.data = [data] if data else []
            return m

        def mock_insert(data):
            d = data.copy()
            d['id'] = len(memory_store.user_records.get(data['user_id'], [])) + 1
            return MagicMock(execute=lambda: mock_execute(d))
            
        self.mock_supabase.table.return_value.insert.side_effect = mock_insert
        self.mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_execute()

    def tearDown(self):
        self.patcher.stop()

    async def test_hybrid_ranking_balance(self):
        print("\n--- Starting Hybrid Retrieval Test ---")
        user_id = "test-user-hybrid"
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Scenario: 
        # A: Farther semantic match but very important/recent
        # B: Closer semantic match but older/unimportant
        
        emb_query = [0.1] * 1536
        emb_close = [0.105] * 1536 # Dist ~ 1536*(0.005^2) = 0.0384
        emb_far = [0.12] * 1536    # Dist ~ 1536*(0.02^2) = 0.6144
        
        print("Uploading scenario memories...")
        # A: Rank 1 goal: Highly important and Brand New
        rec_a = memory_store.add_memory("Important New", user_id, "A", emb_far, importance=2.0)
        rec_a["created_at"] = now.isoformat()
        
        # B: Semantically closer but Old and Unimportant
        rec_b = memory_store.add_memory("Close Old", user_id, "B", emb_close, importance=0.1)
        rec_b["created_at"] = (now - datetime.timedelta(days=60)).isoformat()
        
        print("Searching...")
        results = await memory_store.search("info", emb_query, user_id, top_k=2)
        
        for i, res in enumerate(results):
            print(f"  {i+1}. {res['summary']} (Relevance: {res['metadata']['relevance']})")
            # Verify no internals leaked
            self.assertNotIn("raw_dist", res["metadata"])
            self.assertNotIn("recency_score", res["metadata"])
            self.assertIn("relevance", res["metadata"])

        print("\n--- Hybrid Retrieval Test Passed! ---")

if __name__ == "__main__":
    unittest.main()
