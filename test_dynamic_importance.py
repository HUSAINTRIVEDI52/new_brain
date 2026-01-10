import sys
import os
import unittest
import asyncio
import numpy as np
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.ai import ai_client
from utils.memory_store import memory_store

class TestDynamicImportance(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Mock Supabase
        self.patcher = patch('utils.memory_store.supabase')
        self.mock_supabase = self.patcher.start()
        
        # Reset memory store
        memory_store.user_indices = {}
        memory_store.user_records = {}
        memory_store.user_query_history = {}
        memory_store.user_record_maps = {}
        
        # Mock Supabase insert/update
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

    async def test_importance_bias_ranking(self):
        print("\n--- Starting Dynamic Importance Re-ranking Test ---")
        user_id = "00000000-0000-0000-0000-000000000000"
        
        # 1. Seed two memories
        # emb_a is closer to query than emb_b
        emb_a = [0.1] * 1536
        emb_b = [0.105] * 1536
        query_emb = [0.09] * 1536 # Closer to A
        
        text_a = "The recipe for the secret sauce is kept in a safe."
        text_b = "The direct instructions for the secret sauce are secured."
        
        print("Uploading two memories (A is semantically closer)...")
        rec_a = memory_store.add_memory(text_a, user_id, "Summary A", emb_a)
        rec_b = memory_store.add_memory(text_b, user_id, "Summary B", emb_b)

        # 2. Perform initial search. A should be first because it's closer.
        query = "How do I make the secret sauce?"
        
        print(f"Initial search (A should be first)...")
        results_1 = await memory_store.search(query, query_emb, user_id, top_k=2)
        print(f"  Top result: {results_1[0]['raw_text']} (Dist: {results_1[0]['metadata']['raw_dist']:.4f})")
        self.assertEqual(results_1[0]["id"], rec_a["id"])

        # 3. Simulate Memory B being much more 'important'
        print("\nSimulating frequent access and AI summary influence for Memory B...")
        for _ in range(100):
            await memory_store.get_memory(rec_b["id"], user_id)
        
        # Manually boost summary_count to simulate AI relevance
        memory_store.user_record_maps[user_id][rec_b["id"]]["summary_count"] = 10
        
        # 4. Search again. 
        # Even though they have SAME embedding distance, B should now be first.
        print(f"Post-optimization search (B should now rank higher)...")
        results_2 = await memory_store.search(query, query_emb, user_id, top_k=2)
        
        print(f"  Top result: {results_2[0]['raw_text']} (Imp: {results_2[0]['importance']})")
        print(f"  Second result: {results_2[1]['raw_text']} (Imp: {results_2[1]['importance']})")
        
        self.assertEqual(results_2[0]["id"], rec_b["id"])
        self.assertGreater(results_2[0]["importance"], results_2[1]["importance"])
        
        # 5. Verify normalization
        print("\nVerifying importance normalization...")
        self.assertLessEqual(results_2[0]["importance"], 1.0)
        self.assertGreaterEqual(results_2[0]["importance"], 0.0)

        print("\n--- Dynamic Importance Test Passed! ---")

if __name__ == "__main__":
    unittest.main()
