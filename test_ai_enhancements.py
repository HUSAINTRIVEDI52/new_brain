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
from utils.ai import ai_client

class TestAIEnhancements(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.user_id = "ai-test-user"
        app.dependency_overrides[get_current_user] = lambda: MagicMock(user=MagicMock(id=self.user_id))

    async def test_topic_extraction_on_upload(self):
        print("\n--- Testing Automated Topic Extraction ---")
        
        # Mock AI calls
        with patch('utils.ai.ai_client.get_embedding') as mock_emb, \
             patch('utils.ai.ai_client.summarize_text') as mock_sum, \
             patch('utils.ai.ai_client.extract_topics') as mock_topics:
            
            mock_emb.return_value = [0.0]*1536
            mock_sum.return_value = "This is a summary."
            mock_topics.return_value = ["tech", "coding", "ai"]
            
            # Mock MemoryStore.add_memory
            with patch('utils.memory_store.memory_store.add_memory') as mock_add:
                mock_add.return_value = {
                    "id": 1,
                    "raw_text": "I like coding",
                    "created_at": "2024-01-10T18:00:00Z",
                    "importance": 1.0,
                    "metadata": {"topics": ["tech", "coding", "ai"]}
                }
                
                response = self.client.post("/upload", json={"content": "I like coding"})
                self.assertEqual(response.status_code, 201)
                
                data = response.json()
                self.assertEqual(data["topics"], ["ai", "coding", "tech"])
                print("Verified: Topics automatically extracted and returned in response (Sorted)")

    async def test_session_pooling(self):
        print("\n--- Testing AI Session Pooling ---")
        # Ensure the client is initialized
        self.assertIsNotNone(ai_client._client)
        self.assertFalse(ai_client._client.is_closed)
        print("Verified: AIClient initialized with persistent httpx session")

if __name__ == "__main__":
    unittest.main()
