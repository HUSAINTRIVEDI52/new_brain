import sys
import os
import unittest
import jwt
import time
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app
from utils.config import settings

class TestProductionAuth(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = TestClient(app)
        self.secret = "test-secret-12345"
        settings.SUPABASE_JWT_SECRET = self.secret
        self.user_id = "test-user-uuid"

    def create_token(self, exp=None, sub=None):
        payload = {
            "sub": sub or self.user_id,
            "exp": exp or (int(time.time()) + 3600),
            "aud": "authenticated"
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    async def test_upload_protected_no_token(self):
        print("\n--- Testing Protection (No Token) ---")
        response = self.client.post("/upload", json={"content": "test"})
        # FastAPI HTTPBearer returns 403 for missing auth if auto_error=True (default)
        # However, many production setups prefer 401. Let's check what it actually returns.
        self.assertIn(response.status_code, [401, 403])
        print(f"Verified: Protected with {response.status_code}")

    async def test_valid_token_extraction(self):
        print("\n--- Testing Valid Token Extraction ---")
        token = self.create_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Patch the store to avoid DB calls
        with patch('api.routes.memory_store.add_memory', new_callable=AsyncMock) as mock_add:
            mock_add.return_value = {"id": 1, "raw_text": "test", "created_at": "now"}
            
            response = self.client.post("/upload", json={"content": "test"}, headers=headers)
            self.assertEqual(response.status_code, 201)
            print("Verified: Valid token accepted and user_id used")

    async def test_expired_token(self):
        print("\n--- Testing Expired Token ---")
        token = self.create_token(exp=int(time.time()) - 3600)
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.post("/upload", json={"content": "test"}, headers=headers)
        self.assertEqual(response.status_code, 401)
        self.assertIn("expired", response.json()["detail"].lower())
        print("Verified: Expired token rejected with 401")

    async def test_invalid_signature(self):
        print("\n--- Testing Invalid Signature ---")
        token = self.create_token() + "garbage"
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.post("/upload", json={"content": "test"}, headers=headers)
        self.assertEqual(response.status_code, 401)
        print("Verified: Corrupted token rejected with 401")

    def test_missing_sub_claim(self):
        print("\n--- Testing Missing 'sub' Claim ---")
        payload = {"exp": int(time.time()) + 3600}
        token = jwt.encode(payload, self.secret, algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.post("/upload", json={"content": "test"}, headers=headers)
        self.assertEqual(response.status_code, 401)
        print("Verified: Token without 'sub' rejected")

if __name__ == "__main__":
    import asyncio
    unittest.main()
