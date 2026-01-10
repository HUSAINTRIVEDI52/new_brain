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

class TestMemoryManagement(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = TestClient(app)
        env_secret = getattr(settings, "SUPABASE_JWT_SECRET", None)
        self.secret = env_secret if env_secret else "ebbinghaus-test-secret"
        settings.SUPABASE_JWT_SECRET = self.secret
        self.user_id = "ebbinghaus-manager-uuid"
        self.token = jwt.encode({"sub": self.user_id, "exp": int(time.time()) + 3600}, self.secret, algorithm="HS256")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    async def test_update_memory_success(self):
        print("\n--- Testing PUT /memory/{id} Success ---")
        memory_id = 999
        updates = {"importance": 0.5, "content": "Updated content"}
        
        with patch('api.routes.memory_store.update_memory', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = {
                "id": memory_id, "raw_text": "Updated content", 
                "importance": 0.5, "created_at": "now", "metadata": {}
            }
            
            resp = self.client.put(f"/memory/{memory_id}", json=updates, headers=self.headers)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["content"], "Updated content")
            print("Verified: Memory update successful")

    async def test_delete_memory_success(self):
        print("\n--- Testing DELETE /memory/{id} Success ---")
        memory_id = 888
        
        with patch('api.routes.memory_store.delete_memory', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True
            
            resp = self.client.delete(f"/memory/{memory_id}", headers=self.headers)
            self.assertEqual(resp.status_code, 204)
            print("Verified: Memory deletion successful")

    async def test_management_no_auth(self):
        print("\n--- Testing Management Protection (No Token) ---")
        resp_put = self.client.put("/memory/123", json={"importance": 0.1})
        resp_del = self.client.delete("/memory/123")
        self.assertIn(resp_put.status_code, [401, 403])
        self.assertIn(resp_del.status_code, [401, 403])
        print(f"Verified: Management endpoints are protected (Returned {resp_put.status_code})")

if __name__ == "__main__":
    unittest.main()
