import sys
import os
import unittest
import asyncio
import datetime
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.memory_store import MemoryStore

class TestForgettingEnhancements(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = MemoryStore(dimension=4)
        self.user_id = "ebbinghaus-user"

    def test_reinforcement_logic(self):
        print("\n--- Testing Revisit Reinforcement ---")
        now = datetime.datetime.now(datetime.timezone.utc)
        iso_past = (now - datetime.timedelta(days=10)).isoformat()
        
        # Two identical memories, but one has been revisited 5 times
        m1 = {"id": 1, "created_at": iso_past, "last_accessed_at": iso_past, "importance": 1.0, "access_count": 0}
        m2 = {"id": 2, "created_at": iso_past, "last_accessed_at": iso_past, "importance": 1.0, "access_count": 5}
        
        ret1 = self.store._calculate_retention_score(m1, now=now)
        ret2 = self.store._calculate_retention_score(m2, now=now)
        
        print(f"Single Access Retention: {ret1:.4f}")
        print(f"Multi Access Retention: {ret2:.4f}")
        
        self.assertGreater(ret2, ret1, "Multi-access memory should have higher retention")

    def test_creation_age_decay(self):
        print("\n--- Testing Creation Age Factor ---")
        now = datetime.datetime.now(datetime.timezone.utc)
        iso_now = now.isoformat()
        iso_old = (now - datetime.timedelta(days=365)).isoformat()
        
        # Two memories last accessed exactly NOW, but one was created a year ago
        m_new = {"id": 3, "created_at": iso_now, "last_accessed_at": iso_now, "importance": 1.0, "access_count": 1}
        m_old = {"id": 4, "created_at": iso_old, "last_accessed_at": iso_now, "importance": 1.0, "access_count": 1}
        
        ret_new = self.store._calculate_retention_score(m_new, now=now)
        ret_old = self.store._calculate_retention_score(m_old, now=now)
        
        print(f"New Memory Retention: {ret_new:.4f}")
        print(f"Old Memory Retention: {ret_old:.4f}")
        
        self.assertGreater(ret_new, ret_old, "Older memories should have naturally lower retention even if recently accessed")

    def test_importance_preserving(self):
        print("\n--- Testing Importance-Based Decay Slowing ---")
        now = datetime.datetime.now(datetime.timezone.utc)
        iso_past = (now - datetime.timedelta(days=30)).isoformat()
        
        # Two memories of same age, but one is high importance
        m_normal = {"id": 5, "created_at": iso_past, "last_accessed_at": iso_past, "importance": 1.0, "access_count": 0}
        m_high = {"id": 6, "created_at": iso_past, "last_accessed_at": iso_past, "importance": 3.0, "access_count": 0}
        
        ret_normal = self.store._calculate_retention_score(m_normal, now=now)
        ret_high = self.store._calculate_retention_score(m_high, now=now)
        
        print(f"Normal Importance Retention: {ret_normal:.4f}")
        print(f"High Importance Retention: {ret_high:.4f}")
        
        self.assertGreater(ret_high, ret_normal, "Higher importance memories should decay slower")

    async def test_resurfaced_state_transition(self):
        print("\n--- Testing Resurfaced State Transition ---")
        now = datetime.datetime.now(datetime.timezone.utc)
        # 45 days ago should be 'fading' (Retention around 0.5-0.6)
        iso_long_ago = (now - datetime.timedelta(days=45)).isoformat()
        
        record = {
            "id": 101, "user_id": self.user_id, "created_at": iso_long_ago, 
            "last_accessed_at": iso_long_ago, "importance": 1.0, "access_count": 1
        }
        
        # Initial check
        initial_ret = self.store._calculate_retention_score(record, now=now)
        print(f"Initial Retention: {initial_ret:.4f}")
        self.assertLessEqual(initial_ret, 0.7, "Should start in fading state")
        
        with patch('utils.memory_store.supabase') as mock_sb:
            mock_sb.table().update().eq().eq().execute.return_value = MagicMock()
            
            # Accessing it should return 'resurfaced'
            state = await self.store._update_access_metrics(record, now=now)
            self.assertEqual(state, "resurfaced")
            print("Verified: State transitioned from fading to resurfaced on access")

if __name__ == "__main__":
    unittest.main()
