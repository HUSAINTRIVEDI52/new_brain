from utils.db import supabase
from utils.config import settings
from supabase import create_client
import sys

def test_keys():
    print("--- Supabase Key Diagnostic ---")
    print(f"URL: {settings.SUPABASE_URL}")
    
    # 1. Test Anon Key
    print("\n[1] Testing Anon Key...")
    try:
        # Standard anon key operations usually don't require login for basic health check 
        # but sign_in is the best test
        res = supabase.auth.sign_in_with_password({"email": "nonexistent@test.com", "password": "wrongpassword"})
        print("Anon Key Result:", res)
    except Exception as e:
        print("Anon Key Error:", str(e))
        if "invalid" in str(e).lower() and "key" in str(e).lower():
            print("CRITICAL: The standard SUPABASE_KEY is Invalid.")

    # 2. Test Service Role Key
    print("\n[2] Testing Service Role Key...")
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        print("Service Role Key: MISSING")
    else:
        try:
            admin = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            # Try to list users (requires service_role)
            res = admin.auth.admin.list_users()
            print("Service Role Key: VALID")
            print(f"User count: {len(res.users) if hasattr(res, 'users') else 'unknown'}")
        except Exception as e:
            print("Service Role Key Error:", str(e))
            if "invalid" in str(e).lower() and "key" in str(e).lower():
                print("CRITICAL: The SUPABASE_SERVICE_ROLE_KEY is Invalid.")

if __name__ == "__main__":
    test_keys()
