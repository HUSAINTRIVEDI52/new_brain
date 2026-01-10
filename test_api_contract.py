import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from api.deps import get_current_user

class TestAPIContract(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides[get_current_user] = lambda: MagicMock(user=MagicMock(id="test-user"))

    def test_memory_response_contract(self):
        print("\n--- Testing API Response Contract (Backward Compatibility) ---")
        
        # Mocking MemoryStore.get_all_memories
        with patch('utils.memory_store.memory_store.get_all_memories') as mock_get:
            mock_get.return_value = [{
                "id": 1,
                "raw_text": "Sample content",
                "summary": "Sample summary",
                "importance": 1.0,
                "created_at": "2026-01-10T00:00:00Z",
                "memory_state": "strong",
                "metadata": {"topics": ["test"]}
            }]
            
            response = self.client.get("/memories")
            self.assertEqual(response.status_code, 200)
            
            data = response.json()[0]
            
            # REQUIRED FIELDS FOR FRONTEND STABILITY
            required_fields = ["id", "content", "summary", "importance", "memory_state", "created_at", "topics"]
            for field in required_fields:
                self.assertIn(field, data, f"Missing required field: {field}")
                print(f"Verified: {field} present")

    def test_query_response_contract(self):
        print("\n--- Testing Query Response Contract ---")
        with patch('utils.ai.ai_client.get_embedding') as mock_emb:
            mock_emb.return_value = [0.0]*1536
            
            with patch('utils.memory_store.memory_store.search') as mock_search:
                mock_search.return_value = [{
                    "id": 1,
                    "raw_text": "Query result",
                    "summary": "Short summary",
                    "importance": 0.5,
                    "created_at": "2026-01-10T12:00:00Z",
                    "metadata": {}
                }]
                
                response = self.client.post("/query", json={"query": "test", "top_k": 1})
                self.assertEqual(response.status_code, 200)
                
                data = response.json()
                self.assertIn("results", data)
                self.assertIn("summary", data) # RAG Summary field
                print("Verified: results and summary present in QueryResponse")

if __name__ == "__main__":
    unittest.main()
