import sys
import os
import unittest
import asyncio
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.ai import AIClient

class TestSummarization(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.ai = AIClient()
        self.ai.api_key = "test_key" # Force real logic but mock httpx

    @patch('httpx.AsyncClient.post')
    async def test_single_memory_tone_and_length(self, mock_post):
        print("\n--- Testing Single Memory Tone & Length ---")
        # Mock successful reflective response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "I recall the project kickoff meeting. Everyone was excited about the new architecture. We've set a strong foundation for the year."
                }
            }]
        }
        mock_post.return_value = mock_response

        text = "Project kickoff was great. Everyone scale-out architecture foundation year exciting."
        summary = await self.ai.summarize_text(text)
        
        print(f"Generated Summary: {summary}")
        # Verify sentences count (roughly)
        sentence_count = len([s for s in summary.split('.') if s.strip()])
        self.assertTrue(3 <= sentence_count <= 5, f"Expected 3-5 sentences, got {sentence_count}")
        self.assertIn("recall", summary.lower())
        
    @patch('httpx.AsyncClient.post')
    async def test_rag_grounding_and_fallback(self, mock_post):
        print("\n--- Testing RAG Grounding ---")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "I don't recall any details about Project B. Your notes only mention the success of Project A's architecture."
                }
            }]
        }
        mock_post.return_value = mock_response

        query = "What happened with Project B?"
        memories = ["Project A architecture was a success.", "Used FAISS for Project A."]
        
        summary = await self.ai.generate_search_summary(query, memories)
        print(f"RAG Summary for missing info: {summary}")
        self.assertIn("don't recall", summary.lower())

    @patch('httpx.AsyncClient.post')
    async def test_api_failure_fallback(self, mock_post):
        print("\n--- Testing API Failure Fallback ---")
        mock_post.side_effect = Exception("API Down")

        text = "This is a very long memory that should be truncated in the fallback if the AI fails to generate a proper reflection."
        summary = await self.ai.summarize_text(text)
        
        print(f"Fallback Summary: {summary}")
        self.assertIn("Memory captured", summary)
        self.assertIn("[Summary generation failed]", summary)

if __name__ == "__main__":
    unittest.main()
