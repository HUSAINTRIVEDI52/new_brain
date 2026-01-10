import sys
import os
import asyncio
import time
import numpy as np
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.memory_store import memory_store

async def run_benchmark():
    print("\n--- Starting Search Performance Benchmark ---")
    user_id = "bench-user"
    
    # 1. Mock Supabase
    with patch('utils.memory_store.supabase') as mock_supabase:
        def mock_execute(data=None):
            m = MagicMock()
            m.data = [data] if data else []
            return m

        def mock_insert(data):
            d = data.copy()
            d['id'] = len(memory_store.user_records.get(data['user_id'], [])) + 1
            return MagicMock(execute=lambda: mock_execute(d))
            
        mock_supabase.table.return_value.insert.side_effect = mock_insert
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_execute()

        # 2. Seed 1000 memories
        print("Seeding 1000 memories...")
        start_seed = time.time()
        for i in range(1000):
            emb = np.random.rand(1536).tolist()
            memory_store.add_memory(f"Memory content {i}", user_id, f"Summary {i}", emb)
        end_seed = time.time()
        print(f"Seeding took: {end_seed - start_seed:.2f}s")

        # 3. Benchmark Searches
        print("\nRunning 100 hybrid searches...")
        latencies = []
        for i in range(100):
            query_emb = np.random.rand(1536).tolist()
            start = time.time()
            await memory_store.search(f"query {i}", query_emb, user_id, top_k=5)
            latencies.append(time.time() - start)
        
        avg_latency = sum(latencies) / len(latencies)
        print(f"Average search latency: {avg_latency*1000:.2f}ms")
        print(f"Max search latency: {max(latencies)*1000:.2f}ms")
        print(f"Min search latency: {min(latencies)*1000:.2f}ms")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
