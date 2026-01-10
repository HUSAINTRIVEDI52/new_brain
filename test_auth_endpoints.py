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

class TestAuthEndpoints(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = TestClient(app)
        self.secret = "test-secret-12345"
        settings.SUPABASE_JWT_SECRET = self.secret
        self.user_id = "ebbinghaus-user-uuid"

    def create_mock_supabase_response(self, user_id, email, access_token=None):
        m = MagicMock()
        m.user = MagicMock(id=user_id, email=email)
        if access_token:
            m.session = MagicMock(access_token=access_token)
        else:
            m.session = None
        return m

    async def test_register_success(self):
        print("\n--- Testing Registration Success ---")
        user_data = {"email": "test@example.com", "password": "password123", "name": "Test User"}
        token = jwt.encode({"sub": self.user_id, "exp": int(time.time()) + 3600}, self.secret, algorithm="HS256")
        
        with patch('api.auth.supabase.auth.sign_up') as mock_signup:
            mock_signup.return_value = self.create_mock_supabase_response(self.user_id, user_data["email"], token)
            
            response = self.client.post("/auth/register", json=user_data)
            self.assertEqual(response.status_code, 201)
            data = response.json()
            self.assertEqual(data["user_id"], self.user_id)
            self.assertEqual(data["access_token"], token)
            print("Verified: Registration successful and token returned")

    async def test_register_validation_failures(self):
        print("\n--- Testing Registration Validation ---")
        # 1. Invalid email
        response = self.client.post("/auth/register", json={"email": "bademail", "password": "pass", "name": "X"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json()["detail"].lower())

        # 2. Short password
        response = self.client.post("/auth/register", json={"email": "a@b.com", "password": "123", "name": "X"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("at least 6 characters", response.json()["detail"].lower())

        # 3. Missing name
        response = self.client.post("/auth/register", json={"email": "a@b.com", "password": "password123", "name": " "})
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json()["detail"].lower())
        print("Verified: All validation rules enforced")

    async def test_login_success(self):
        print("\n--- Testing Login Success ---")
        user_data = {"email": "test@example.com", "password": "password123"}
        token = jwt.encode({"sub": self.user_id, "exp": int(time.time()) + 3600}, self.secret, algorithm="HS256")
        
        with patch('api.auth.supabase.auth.sign_in_with_password') as mock_login:
            mock_login.return_value = self.create_mock_supabase_response(self.user_id, user_data["email"], token)
            
            response = self.client.post("/auth/login", json=user_data)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["access_token"], token)
            print("Verified: Login successful and token returned")

    async def test_login_failure(self):
        print("\n--- Testing Login Failure (401) ---")
        with patch('api.auth.supabase.auth.sign_in_with_password') as mock_login:
            mock_login.side_effect = Exception("Invalid login credentials")
            
            response = self.client.post("/auth/login", json={"email": "a@b.com", "password": "wrong"})
            self.assertEqual(response.status_code, 401)
            print("Verified: Invalid credentials return 401")

    async def test_protected_route_with_login_token(self):
        print("\n--- Testing Integration: Token consistency ---")
        # 1. Simulate login to get token
        token = jwt.encode({"sub": self.user_id, "exp": int(time.time()) + 3600}, self.secret, algorithm="HS256")
        
        # 2. Use token on protected route
        headers = {"Authorization": f"Bearer {token}"}
        with patch('api.routes.memory_store.add_memory', new_callable=AsyncMock) as mock_add:
            mock_add.return_value = {"id": 1, "raw_text": "test", "created_at": "now"}
            
            response = self.client.post("/upload", json={"content": "test"}, headers=headers)
            self.assertEqual(response.status_code, 201)
            print("Verified: Token from auth flow works perfectly on memory endpoints")

if __name__ == "__main__":
    unittest.main()
