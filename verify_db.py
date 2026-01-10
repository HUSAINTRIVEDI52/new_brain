from utils.db import supabase, get_supabase_client
from utils.config import settings
import sys

def verify_db():
    print(f"Supabase connection check...")
    
    if not settings.SUPABASE_URL or "your_supabase_url" in settings.SUPABASE_URL:
        print("Skipping DB check: SUPABASE_URL not configured.")
        return

    try:
        # Try a simple select. 
        # Note: This might fail if the table doesn't exist or RLS blocks it.
        # But it confirms the client is initialized.
        response = supabase.table("memories").select("*").limit(1).execute()
        print(f"Connection successful. Data: {response.data}")
    except Exception as e:
        print(f"Connection failed or query error: {e}")

if __name__ == "__main__":
    verify_db()
