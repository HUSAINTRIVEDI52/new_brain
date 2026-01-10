import sys
import os
import unittest
import asyncio
import time
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from api.deps import get_current_user
from utils.memory_store import memory_store

class TestQueryOptimization(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.user_id = "opt-test-user"
        app.dependency_overrides[get_current_user] = lambda: MagicMock(user=MagicMock(id=self.user_id))

    async def test_upstream_cache_bypass_ai(self):
        print("\n--- Testing Upstream Cache (AI Bypass) ---")
        
        # 1. Manually prime the cache
        memory_store.query_results_cache[self.user_id] = {
            ("fast-query", 5): [{"id": 1, "content": "Cached", "summary": "", "importance": 1.0, "memory_state": "strong", "created_at": "2024", "topics": []}]
        }
        
        with patch('utils.ai.ai_client.get_embedding') as mock_emb:
            # First call without summary
            response = self.client.post("/query", json={"query": "fast-query", "top_k": 5})
            self.assertEqual(response.status_code, 200)
            mock_emb.assert_not_called()
            print("Verified: AI embedding skipped for cached query")

    @patch('utils.memory_store.supabase')
    async def test_batch_record_resolution(self, mock_sb):
        print("\n--- Testing Batch DB Resolution ---")
        # Setup memory store with empty caches for user
        memory_store.user_records[self.user_id] = []
        memory_store.user_record_maps[self.user_id] = {}
        
        # Mock vector search returning 3 IDs (none in cache)
        mock_vec = MagicMock()
        async def mock_search(*args): return [(101, 0.1), (102, 0.2), (103, 0.3)]
        mock_vec.search_vectors = mock_search
        memory_store.vector_store = mock_vec
        
        # Mock AI embedding
        with patch('utils.ai.ai_client.get_embedding') as mock_emb:
            mock_emb.return_value = [0.0]*1536
            
            # Perform query
            response = self.client.post("/query", json={"query": "batch-me", "top_k": 5})
            self.assertEqual(response.status_code, 200, f"Query failed: {response.json()}")
            
            # Verify batch call was recorded on the mock
            # The chain is table().select().in_().execute()
            mock_sb.table.assert_called_with("memories")
            # We check if 'in_' was called at any point in the chain
            # Given how postgrest-py works, in_ is a method on the builder
            found_in = False
            for call in mock_sb.table().select().mock_calls:
                if call[0] == 'in_':
                    found_in = True
                    self.assertEqual(call.args[0], "id")
                    self.assertEqual(set(call.args[1]), {101, 102, 103})
                    print(f"Verified: Batch resolve called with IDs: {call.args[1]}")
                    break
            self.assertTrue(found_in, "Batch resolution .in_() call not found")

if __name__ == "__main__":
    memory_store.query_results_cache = {} # Clear for test
    unittest.main()
