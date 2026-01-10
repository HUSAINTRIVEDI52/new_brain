import sys
import os
import unittest
import asyncio
import numpy as np
import time
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.ai import ai_client
from utils.memory_store import memory_store

class TestMultiUserSearch(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Mock Supabase to avoid RLS/Network noise
        self.patcher = patch('utils.memory_store.supabase')
        self.mock_supabase = self.patcher.start()
        
        # Reset memory store
        memory_store.user_indices = {}
        memory_store.user_records = {}
        
        # Mock Supabase insert
        def mock_insert(data):
            mock_res = MagicMock()
            data_with_id = data.copy()
            data_with_id['id'] = 100 # Dummy ID
            mock_res.data = [data_with_id]
            return MagicMock(execute=lambda: mock_res)
        self.mock_supabase.table.return_value.insert.side_effect = mock_insert

    def tearDown(self):
        self.patcher.stop()

    async def test_isolation_and_performance(self):
        print("\n--- Starting Multi-User Isolation & Performance Test ---")
        user_a = "00000000-0000-0000-0000-000000000001"
        user_b = "00000000-0000-0000-0000-000000000002"
        
        # 1. Seed Data for User A (Space)
        print("Seeding Space data for User A...")
        space_notes = [
            "The Hubble Space Telescope has provided beautiful images.",
            "Mars is known as the Red Planet.",
            "Black holes are regions of space-time where gravity is strong."
        ]
        for note in space_notes:
            emb = await ai_client.get_embedding(note)
            memory_store.add_memory(note, user_a, "Summary", emb)

        # 2. Seed Data for User B (Cooking)
        print("Seeding Cooking data for User B...")
        cooking_notes = [
            "Pasta carbonara requires eggs, cheese, and guanciale.",
            "The Maillard reaction is responsible for browning food.",
            "Baking bread requires flour, water, salt, and yeast."
        ]
        for note in cooking_notes:
            emb = await ai_client.get_embedding(note)
            memory_store.add_memory(note, user_b, "Summary", emb)

        # 3. Query User A about "Cooking" 
        # (Should return NOTHING or unrelated items from user_a ONLY)
        print("\nQuerying User A (Space fan) about 'How to cook eggs'...")
        query_text = "How to cook eggs"
        query_emb = await ai_client.get_embedding(query_text)
        
        start_time = time.time()
        results_a = memory_store.search(query_emb, user_a, top_k=2)
        end_time = time.time()
        
        print(f"Search latency: {(end_time - start_time)*1000:.2f}ms")
        
        print("Results for User A:")
        for r in results_a:
            print(f"  - {r['raw_text']}")
            self.assertEqual(r['user_id'], user_a) # STRICT ISOLATION CHECK
            self.assertNotIn("Pasta", r['raw_text'])

        # 4. Query User B about "Cooking" 
        print("\nQuerying User B (Chef) about 'How to cook eggs'...")
        results_b = memory_store.search(query_emb, user_b, top_k=2)
        
        print("Results for User B:")
        for r in results_b:
            print(f"  - {r['raw_text']}")
            self.assertEqual(r['user_id'], user_b) # STRICT ISOLATION CHECK
        
        self.assertTrue(any("Pasta" in r['raw_text'] or "Maillard" in r['raw_text'] for r in results_b))
        
        # 5. Verify Embedding Cache
        print("\nVerifying Embedding Cache...")
        start_cache = time.time()
        await ai_client.get_embedding(query_text) # Should be instant
        end_cache = time.time()
        cache_latency = (end_cache - start_cache)*1000
        print(f"Cached embedding latency: {cache_latency:.2f}ms")
        self.assertLess(cache_latency, 1.0) # Should be sub-millisecond

        print("\n--- Multi-User Test Passed! ---")

if __name__ == "__main__":
    unittest.main()
