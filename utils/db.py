from supabase import create_client, Client
from utils.config import settings

def get_supabase_client() -> Client:
    url: str = settings.SUPABASE_URL
    key: str = settings.SUPABASE_KEY
    if not url or not key:
        return None
    return create_client(url, key)

supabase: Client = get_supabase_client()
