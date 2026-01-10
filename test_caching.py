import sys
import os
import unittest
import asyncio
import time
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.ai import ai_client
from utils.memory_store import memory_store

class TestCachingLayer(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Mock Supabase
        self.patcher = patch('utils.memory_store.supabase')
        self.mock_supabase = self.patcher.start()
        
        # Reset memory store
        memory_store.user_indices = {}
        memory_store.user_records = {}
        memory_store.user_record_maps = {}
        memory_store.query_results_cache = {}
        
        # Mock Supabase insert
        def mock_insert(data):
            mock_res = MagicMock()
            data_with_id = data.copy()
            data_with_id['id'] = len(memory_store.user_records.get(data['user_id'], [])) + 1
            mock_res.data = [data_with_id]
            return MagicMock(execute=lambda: mock_res)
        self.mock_supabase.table.return_value.insert.side_effect = mock_insert

    def tearDown(self):
        self.patcher.stop()

    async def test_cache_and_invalidation(self):
        print("\n--- Starting Caching Layer Integration Test ---")
        user_id = "00000000-0000-0000-0000-000000000000"
        
        # 1. Add some initial data
        print("Seeding initial data...")
        note_1 = "The moon orbits the Earth."
        emb_1 = await ai_client.get_embedding(note_1)
        memory_store.add_memory(note_1, user_id, "Moon info", emb_1)

        note_2 = "Gravity keeps us on the ground."
        emb_2 = await ai_client.get_embedding(note_2)
        memory_store.add_memory(note_2, user_id, "Gravity info", emb_2)

        # 2. First Search (Cache MISS)
        query = "Tell me about space"
        query_emb = await ai_client.get_embedding(query)
        
        print(f"Query 1: '{query}' (Expect MISS)")
        start_1 = time.time()
        res_1 = memory_store.search(query, query_emb, user_id, top_k=5)
        end_1 = time.time()
        print(f"  Latency: {(end_1 - start_1)*1000:.4f}ms")
        self.assertEqual(len(res_1), 2)

        # 3. Second Search (Cache HIT)
        print(f"Query 2: '{query}' (Expect HIT)")
        start_2 = time.time()
        res_2 = memory_store.search(query, query_emb, user_id, top_k=5)
        end_2 = time.time()
        print(f"  Latency: {(end_2 - start_2)*1000:.4f}ms")
        self.assertEqual(res_1, res_2)
        self.assertLess(end_2 - start_2, end_1 - start_1)

        # 4. Invalidation Test
        print("\nAdding new memory (Expect cache invalidation)...")
        note_3 = "The Sun is a yellow dwarf star."
        emb_3 = await ai_client.get_embedding(note_3)
        memory_store.add_memory(note_3, user_id, "Sun info", emb_3)
        
        # Search again (Expect MISS and 3 results)
        print(f"Query 3: '{query}' (Expect MISS after invalidation)")
        start_3 = time.time()
        res_3 = memory_store.search(query, query_emb, user_id, top_k=5)
        end_3 = time.time()
        print(f"  Latency: {(end_3 - start_3)*1000:.4f}ms")
        self.assertEqual(len(res_3), 3)
        self.assertIn("Sun", res_3[0]['raw_text'] + res_3[1]['raw_text'] + res_3[2]['raw_text'])

        # 5. Fast Lookup Test
        print("\nVerifying O(1) Lookup...")
        m_id = res_3[0]['id']
        start_4 = time.time()
        m_rec = memory_store.get_memory(m_id, user_id)
        end_4 = time.time()
        print(f"  Lookup Latency: {(end_4 - start_4)*1000:.4f}ms")
        self.assertEqual(m_rec['id'], m_id)

        print("\n--- Caching Layer Test Passed! ---")

if __name__ == "__main__":
    unittest.main()
