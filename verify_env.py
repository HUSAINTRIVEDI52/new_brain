from utils.config import settings
import sys

def verify_settings():
    print(f"Project: {settings.PROJECT_NAME}")
    print(f"Environment: {settings.API_ENV}")
    
    # Check Supabase
    if settings.SUPABASE_URL == "your_supabase_url_here":
         print("Supabase URL: Loaded (Placeholder)")
    else:
         print(f"Supabase URL: {settings.SUPABASE_URL}")

    if settings.SUPABASE_KEY == "your_supabase_anon_key_here":
         print("Supabase Key: Loaded (Placeholder)")
    else:
         print("Supabase Key: [HIDDEN]")

    # Check OpenRouter
    if settings.OPENROUTER_API_KEY == "your_openrouter_key_here":
         print("OpenRouter Key: Loaded (Placeholder)")
    else:
         print("OpenRouter Key: [HIDDEN]")

    if not settings.SUPABASE_URL:
        print("ERROR: SUPABASE_URL is missing")
        sys.exit(1)
        
    print("\nEnvironment verification successful.")

if __name__ == "__main__":
    verify_settings()
