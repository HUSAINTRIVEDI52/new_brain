import jwt
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from utils.db import supabase
from utils.config import settings
from utils.logger import log_event

security = HTTPBearer()
logger = logging.getLogger(__name__)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Verifies the JWT token and returns the user_id (sub).
    Usage: user_id = Depends(get_current_user)
    """
    token = credentials.credentials
    
    # 1. High-Performance Local Verification (if secret available)
    if settings.SUPABASE_JWT_SECRET:
        try:
            # Supabase uses HS256 for the JWT_SECRET
            payload = jwt.decode(
                token, 
                settings.SUPABASE_JWT_SECRET, 
                algorithms=["HS256"],
                options={"verify_aud": False} # Supabase tokens often have 'authenticated' aud
            )
            user_id = payload.get("sub")
            if not user_id:
                raise ValueError("Missing 'sub' claim in token")
            return user_id
        except jwt.ExpiredSignatureError:
            log_event(logging.WARNING, "auth_expired", "Token expired", status="401")
            raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
        except jwt.InvalidTokenError as e:
            log_event(logging.WARNING, "auth_invalid", f"Invalid token: {e}", status="401")
            raise HTTPException(status_code=401, detail="Invalid authentication token.")
        except Exception as e:
            logger.error(f"Auth error: {e}")
            # Fallback to Supabase API if local fails but secret exists (defensive)
            pass

    # 2. Fallback to Supabase API (Durable but slower)
    try:
        response = supabase.auth.get_user(token)
        if hasattr(response, "user") and response.user:
            return str(response.user.id)
        
        # Some versions of supabase-py return the user directly or in .user
        if isinstance(response, dict) and "user" in response:
            return response["user"]["id"]
            
        raise HTTPException(status_code=401, detail="Invalid session.")
    except Exception as e:
        log_event(logging.ERROR, "auth_api_failed", str(e), status="401")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Please check your credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
