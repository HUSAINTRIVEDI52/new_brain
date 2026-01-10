from dotenv import load_dotenv
import os

load_dotenv()

key = os.getenv("SUPABASE_KEY", "")
url = os.getenv("SUPABASE_URL", "")

print(f"--- Configuration Check ---")
print(f"SUPABASE_URL: {url}")
print(f"SUPABASE_KEY Length: {len(key)}")

if not key:
    print("ERROR: SUPABASE_KEY is empty.")
elif key.startswith("sb_publishable"):
    print("ERROR: Invalid Key Type Detected!")
    print("       You are using the 'Publishable API Key' (starts with 'sb_publishable').")
    print("       The Python client REQUIRES the 'anon' / 'public' key.")
    print("       This key usually starts with 'eyJ' and is a long JWT token.")
elif key.startswith("eyJ"):
    print("SUCCESS: Key format appears to be a valid JWT (starts with 'eyJ').")
    print("         If connection still fails, check if the key belongs to THIS project.")
else:
    print(f"WARNING: Key starts with '{key[:5]}...' which is unexpected.")
    print("         Ensure you copied the 'anon' key.")
