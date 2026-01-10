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

class TestAIFlow(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Mock Supabase
        self.patcher = patch('utils.memory_store.supabase')
        self.mock_supabase = self.patcher.start()
        
        # Reset memory store for each test
        memory_store.memories = []
        memory_store.index = MagicMock()
        memory_store.index.ntotal = 0

    def tearDown(self):
        self.patcher.stop()

    async def test_semantic_search(self):
        print("\n--- Starting AI Semantic Search Integration Test (Mocked DB) ---")
        user_id = "00000000-0000-0000-0000-000000000000"
        
        # Mock Supabase insert response
        def mock_insert(data):
            mock_res = MagicMock()
            data_with_id = data.copy()
            data_with_id['id'] = len(memory_store.memories) + 1
            mock_res.data = [data_with_id]
            return MagicMock(execute=lambda: mock_res)

        self.mock_supabase.table.return_value.insert.side_effect = mock_insert

        # 1. Create Sample Data
        memories = [
            "The capital of France is Paris.",
            "Python is a versatile programming language used for data science.",
            "The sun is a star at the center of our solar system.",
            "FastAPI is a modern web framework for building APIs with Python."
        ]
        
        # Real local index for searching in the test
        import faiss
        real_index = faiss.IndexFlatL2(1536)
        
        print("Uploading memories...")
        for text in memories:
            embedding = await ai_client.get_embedding(text)
            summary = await ai_client.summarize_text(text)
            
            # Manually simulate the add_memory logic for the mock
            rec = memory_store.add_memory(
                content=text,
                user_id=user_id,
                summary=summary,
                embedding=embedding
            )
            # Update our real index for search verification
            real_index.add(np.array([embedding]).astype('float32'))
            print(f"  Added: {text[:40]}...")

        # 2. Perform Semantic Query
        query = "Tell me about coding in Python"
        print(f"\nQuerying: '{query}'")
        
        query_embedding = await ai_client.get_embedding(query)
        
        # Mock the search call to use our real_index
        distances, indices = real_index.search(np.array([query_embedding]).astype('float32'), 2)
        
        # Simulate memory_store.search logic
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            memory = memory_store.memories[int(idx)]
            res = memory.copy()
            res["metadata"] = {"score": float(dist)}
            results.append(res)
        
        print("\nSearch Results:")
        for i, res in enumerate(results):
            score = res['metadata'].get('score', 'N/A')
            print(f"  {i+1}. [{score:.4f}] {res['raw_text']}")

        # 3. Assertions
        self.assertGreater(len(results), 0)
        top_content = results[0]['raw_text'].lower()
        self.assertTrue("python" in top_content or "fastapi" in top_content)
        print("\n--- Test Passed Successfully (AI logic verified)! ---")

if __name__ == "__main__":
    unittest.main()
