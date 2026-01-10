import sys
import os
import unittest
import asyncio
import datetime
import logging
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.ai import ai_client
from utils.memory_store import memory_store

class TestForgettingCurve(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Configure logging to show debug messages
        logging.basicConfig(level=logging.DEBUG)
        
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
            # Create a return object that mimics Supabase's response.data
            # IMPORTANT: Return real dicts, not MagicMocks
            return_record = data.copy()
            return_record['id'] = 1
            
            mock_res = MagicMock()
            mock_res.data = [return_record]
            
            mock_execute = MagicMock()
            mock_execute.execute.return_value = mock_res
            return mock_execute
        
        self.mock_supabase.table.return_value.insert.side_effect = mock_insert
        
        # Mock Supabase update
        mock_update_res = MagicMock()
        mock_update_res.data = []
        self.mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update_res

    def tearDown(self):
        self.patcher.stop()

    async def test_state_transitions(self):
        print("\n--- Starting Forgetting Curve Logic Test ---")
        user_id = "00000000-0000-0000-0000-000000000000"
        
        # 1. Upload a memory (Fixed time)
        now = datetime.datetime(2026, 1, 10, 10, 0, 0, tzinfo=datetime.timezone.utc)
        with patch('utils.memory_store.datetime.datetime') as mock_date:
            mock_date.now.return_value = now
            mock_date.fromisoformat = datetime.datetime.fromisoformat
            
            note = "I need to remember this important fact."
            emb = await ai_client.get_embedding(note)
            
            print("Uploading memory at T=0...")
            rec = memory_store.add_memory(note, user_id, "Summary", emb, importance=1.0)
            self.assertEqual(rec["memory_state"], "strong")

        # 2. Simulate time passage (e.g., 10 days later)
        ten_days_later = now + datetime.timedelta(days=10)
        print("Checking state after 10 days...")
        all_m = memory_store.get_all_memories(user_id)
        # Manually calculate state with mock time
        state_after_10 = memory_store._calculate_memory_state(all_m[0], now=ten_days_later)
        self.assertEqual(state_after_10, "fading")
        
        # Update local record to simulate the fading state before access
        all_m[0]["memory_state"] = "fading"
        
        # 3. Access memory (should resurface)
        print("Accessing 'fading' memory (Expect resurfaced)...")
        res = await memory_store.get_memory(rec["id"], user_id, now=ten_days_later)
        self.assertEqual(res["memory_state"], "resurfaced")
        
        # 4. Access again (should be strong)
        print("Accessing again (Expect strong)...")
        res_2 = await memory_store.get_memory(rec["id"], user_id, now=ten_days_later)
        self.assertEqual(res_2["memory_state"], "strong")
        self.assertEqual(res_2["access_count"], 2)

    async def test_importance_impact(self):
        print("\n--- Testing Importance Impact ---")
        user_id = "00000000-0000-0000-0000-000000000000"
        
        now = datetime.datetime(2026, 1, 10, 10, 0, 0, tzinfo=datetime.timezone.utc)
        with patch('utils.memory_store.datetime.datetime') as mock_date:
            mock_date.now.return_value = now
            mock_date.fromisoformat = datetime.datetime.fromisoformat
            
            # High importance vs Low importance
            emb = await ai_client.get_embedding("test")
            
            print("Uploading high importance memory (10.0)...")
            rec_high = memory_store.add_memory("Important", user_id, "S", emb, importance=10.0)
            
            print("Uploading low importance memory (0.1)...")
            rec_low = memory_store.add_memory("Minor", user_id, "S", emb, importance=0.1)

        # 2 days later
        # Low importance (0.1): d = 0.5 / (0.1 * 1) = 5. e^(-5*2) = e^-10 (fading)
        # High importance (10): d = 0.5 / (10 * 1) = 0.05. e^(-0.05*2) = e^-0.1 (strong)
        
        two_days_later = now + datetime.timedelta(days=2)
        print("Checking states after 2 days...")
        all_m = memory_store.get_all_memories(user_id)
        # Use the explicit time for state calculation in test
        states = {m["raw_text"]: memory_store._calculate_memory_state(m, now=two_days_later) for m in all_m}
        
        print(f"  High Imp: {states['Important']}")
        print(f"  Low Imp: {states['Minor']}")
        
        self.assertEqual(states["Important"], "strong")
        self.assertEqual(states["Minor"], "fading")

        print("\n--- Forgetting Curve Test Passed! ---")

if __name__ == "__main__":
    unittest.main()
