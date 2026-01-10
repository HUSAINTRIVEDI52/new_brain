import requests
import time
import subprocess
import sys
import os

# Start the server in the background
process = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--port", "8000"], 
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print("Starting server...")
time.sleep(5)  # Wait for server to start

base_url = "http://localhost:8000"

try:
    # 1. Test Health Check
    response = requests.get(f"{base_url}/")
    print(f"GET /: {response.status_code} - {response.json()}")
    assert response.status_code == 200

    # 2. Test Upload
    response = requests.post(f"{base_url}/upload", json={"content": "Test memory", "metadata": {"tag": "test"}})
    print(f"POST /upload: {response.status_code} - {response.json()}")
    assert response.status_code == 200

    # 3. Test Query
    response = requests.post(f"{base_url}/query", json={"query": "something", "top_k": 3})
    print(f"POST /query: {response.status_code} - {response.json()}")
    assert response.status_code == 200

    # 4. Test Get Memory
    response = requests.get(f"{base_url}/memory/1")
    print(f"GET /memory/1: {response.status_code} - {response.json()}")
    assert response.status_code == 200

    # 5. Test Get All Memories
    response = requests.get(f"{base_url}/memories")
    print(f"GET /memories: {response.status_code} - {response.json()}")
    assert response.status_code == 200
    
    print("\nAll tests passed!")

except Exception as e:
    print(f"\nTests failed: {e}")
finally:
    process.terminate()
    print("Server terminated.")
