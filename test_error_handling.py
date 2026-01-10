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

class TestErrorHandling(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Mock auth via dependency overrides
        app.dependency_overrides[get_current_user] = lambda: MagicMock(user=MagicMock(id="test-user"))

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_upload_empty_content(self):
        print("\n--- Testing Upload Empty Content ---")
        response = self.client.post("/upload", json={"content": "  ", "importance": 1.0})
        print(f"Response: {response.json()}")
        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot be empty", response.json()["detail"])

    @patch('utils.ai.httpx.AsyncClient.post')
    def test_upload_service_error_leakage(self, mock_post):
        print("\n--- Testing Error Leakage Prevention ---")
        # Simulate a crashy external service or internal bug
        mock_post.side_effect = Exception("INTERNAL_DB_CRASH_VERBOSE_TRACESTACK")
        
        response = self.client.post("/upload", json={"content": "Valid content", "importance": 1.0})
        print(f"Response: {response.json()}")
        
        self.assertEqual(response.status_code, 500)
        # Verify no technical terms are in the response
        detail = response.json()["detail"].lower()
        self.assertNotIn("internal_db_crash", detail)
        self.assertNotIn("tracestack", detail)
        self.assertIn("an error occurred", detail)

    def test_query_empty_string(self):
        print("\n--- Testing Query Empty String ---")
        response = self.client.post("/query", json={"query": " "})
        print(f"Response: {response.json()}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["results"], [])
        self.assertIn("Please provide a search query", data["summary"])

    @patch('utils.ai.AIClient.get_embedding')
    async def test_search_zero_vector_fallback(self, mock_emb):
        print("\n--- Testing Search Zero-Vector Fallback ---")
        # Mocking get_embedding to fail/return 0-vector
        mock_emb.return_value = [0.0] * 1536
        
        from utils.memory_store import memory_store
        results = await memory_store.search("query", [0.0]*1536, "test-user")
        # Should just be an empty list if nothing matches the 0-vector well enough (it won't)
        self.assertIsInstance(results, list)
        print("Search with zero-vector fallback completed without crash.")

if __name__ == "__main__":
    unittest.main()
