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

class TestRegistrationFix(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = TestClient(app)
        env_secret = getattr(settings, "SUPABASE_JWT_SECRET", None)
        self.secret = env_secret if env_secret else "ebbinghaus-fix-secret"
        settings.SUPABASE_JWT_SECRET = self.secret
        self.user_id = "ebbinghaus-fix-user-uuid"

    def create_mock_response(self, has_session=True):
        m = MagicMock()
        m.user = MagicMock(id=self.user_id)
        if has_session:
            token = jwt.encode({"sub": self.user_id, "exp": int(time.time()) + 3600}, self.secret, algorithm="HS256")
            m.session = MagicMock(access_token=token)
        else:
            m.session = None
        return m

    async def test_register_with_immediate_session(self):
        print("\n--- Testing Registration with immediate session ---")
        with patch('api.auth.supabase.auth.sign_up') as mock_signup, \
             patch('api.auth.supabase.auth.get_user') as mock_get_user:
            
            mock_signup.return_value = self.create_mock_response(has_session=True)
            mock_get_user.return_value = MagicMock()
            
            resp = self.client.post("/auth/register", json={
                "email": "test@fix.com", "password": "Password123", "name": "Fixer"
            })
            self.assertEqual(resp.status_code, 201)
            self.assertTrue(len(resp.json()["access_token"]) > 0)
            print("Verified: Success when sign_up returns token immediately")

    async def test_register_with_fallback_login(self):
        print("\n--- Testing Registration with sign-in fallback ---")
        with patch('api.auth.supabase.auth.sign_up') as mock_signup, \
             patch('api.auth.supabase.auth.sign_in_with_password') as mock_signin, \
             patch('api.auth.supabase.auth.get_user') as mock_get_user:
            
            # sign_up returns user but NO session
            mock_signup.return_value = self.create_mock_response(has_session=False)
            # fallback sign_in returns session
            mock_signin.return_value = self.create_mock_response(has_session=True)
            mock_get_user.return_value = MagicMock()
            
            resp = self.client.post("/auth/register", json={
                "email": "test@fallback.com", "password": "Password123", "name": "Fixer"
            })
            self.assertEqual(resp.status_code, 201)
            self.assertTrue(len(resp.json()["access_token"]) > 0)
            self.assertEqual(mock_signin.call_count, 1)
            print("Verified: Success via fallback login when sign_up is session-less")

    async def test_register_failure_no_token(self):
        print("\n--- Testing Registration failure when no token possible ---")
        with patch('api.auth.supabase.auth.sign_up') as mock_signup, \
             patch('api.auth.supabase.auth.sign_in_with_password') as mock_signin:
            
            mock_signup.return_value = self.create_mock_response(has_session=False)
            mock_signin.side_effect = Exception("Email not confirmed")
            
            resp = self.client.post("/auth/register", json={
                "email": "test@fail.com", "password": "Password123", "name": "Fixer"
            })
            self.assertEqual(resp.status_code, 401)
            self.assertIn("verify your email", resp.json()["detail"].lower())
            print("Verified: Correct 401 response when token cannot be acquired")

if __name__ == "__main__":
    unittest.main()
