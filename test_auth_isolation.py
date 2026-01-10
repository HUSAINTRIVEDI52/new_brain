import sys
import os
import unittest
import asyncio
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from api.deps import get_current_user

class TestAuthIsolation(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TestClient(app)
        # We will override this in specific tests
        app.dependency_overrides.clear()

    @patch('utils.memory_store.supabase')
    def test_cross_user_get_fail(self, mock_supabase):
        print("\n--- Testing Cross-User Access Prevention ---")
        user_a = "user-a"
        user_b = "user-b"
        
        # 1. Mock user A memory in global store
        from utils.memory_store import memory_store
        memory_store.user_record_maps[user_a] = {1: {"id": 1, "user_id": user_a, "raw_text": "A's secret"}}
        memory_store.user_record_maps[user_b] = {} # B has nothing
        
        # 2. Authenticate as User B
        app.dependency_overrides[get_current_user] = lambda: MagicMock(user=MagicMock(id=user_b))
        
        # 3. Try to GET User A's memory
        response = self.client.get("/memory/1")
        print(f"User B requesting User A's memory: {response.status_code}")
        
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"].lower())

    @patch('utils.ai.httpx.AsyncClient.post')
    @patch('utils.memory_store.supabase')
    def test_cross_user_query_isolation(self, mock_supabase, mock_ai):
        print("\n--- Testing Search Result Isolation ---")
        user_a = "user-a"
        user_b = "user-b"
        
        from utils.memory_store import memory_store
        # Reset store for clean test
        memory_store.user_records = {user_a: [], user_b: []}
        memory_store.user_indices = {}
        
        # Seed user A with something
        memory_store.user_records[user_a] = [{"id": 1, "user_id": user_a, "raw_text": "Secret A"}]
        # Seed user B with something else
        memory_store.user_records[user_b] = [{"id": 2, "user_id": user_b, "raw_text": "Public B"}]
        
        # 2. Authenticate as User B
        app.dependency_overrides[get_current_user] = lambda: MagicMock(user=MagicMock(id=user_b))
        
        # Mocking embedding to return 0-vector
        mock_ai.return_value = MagicMock(status_code=200, json=lambda: {"data": [{"embedding": [0.0]*1536}]})
        
        # 3. Search as User B
        response = self.client.post("/query", json={"query": "secret", "top_k": 5})
        print(f"Search results count for User B: {len(response.json()['results'])}")
        
        results = response.json()["results"]
        for res in results:
            self.assertEqual(res["id"], 2) # Should ONLY see their own (Public B)
            self.assertNotEqual(res["id"], 1)

if __name__ == "__main__":
    unittest.main()
