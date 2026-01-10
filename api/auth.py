import logging
import re
from fastapi import APIRouter, HTTPException, status
from models.schemas import UserRegister, UserLogin, TokenResponse
from utils.db import supabase
from utils.config import settings
from utils.logger import log_event

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

def validate_email(email: str) -> bool:
    # Basic but robust regex for email validation
    return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email))

def validate_password_strength(password: str) -> bool:
    # At least 8 characters, mix of letters and numbers
    if len(password) < 8:
        return False
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)
    return has_letter and has_number

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    """
    Registers a new user with strict validation and returns a JWT access token.
    """
    email = user_data.email.strip().lower()
    name = user_data.name.strip()
    
    # 1. Validation Logic
    if not validate_email(email):
        raise HTTPException(
            status_code=400, 
            detail=f"Registration failed: Email address '{email}' is invalid"
        )
    
    if not validate_password_strength(user_data.password):
        raise HTTPException(
            status_code=400, 
            detail="Registration failed: Password must be at least 8 characters long and contain both letters and numbers"
        )

    if not name:
        raise HTTPException(status_code=400, detail="Registration failed: Name is required")

    try:
        # 2. Supabase Sign Up
        auth_dict = {
            "email": email,
            "password": user_data.password,
            "options": {
                "data": {
                    "name": name
                }
            }
        }
        
        logger.info(f"Attempting sign-up for sanitized email: '{email}'")
        
        try:
            response = supabase.auth.sign_up(auth_dict)
            if not response.user:
                raise Exception("user_not_created")
        except Exception as e:
            err_msg = str(e).lower()
            # Detect rate limit or verification issues
            if ("rate limit" in err_msg or "email_limit_exceeded" in err_msg) and settings.SUPABASE_SERVICE_ROLE_KEY:
                logger.warning(f"Registration rate limited. Falling back to Admin API for '{email}'")
                from supabase import create_client
                admin_supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
                
                # Admin creation bypass
                admin_resp = admin_supabase.auth.admin.create_user({
                    "email": email,
                    "password": user_data.password,
                    "user_metadata": {"name": name},
                    "email_confirm": True
                })
                
                if not admin_resp.user:
                    raise HTTPException(status_code=400, detail=f"Admin registration failed: {str(e)}")
                
                # Manual sign-in to get a session
                login_resp = supabase.auth.sign_in_with_password({"email": email, "password": user_data.password})
                if not login_resp.session:
                    raise HTTPException(status_code=401, detail="Account created via Admin API, but auto-login failed. Please sign in manually.")
                
                response = login_resp
            else:
                # Re-raise for standard error handling
                raise

        user_id = str(response.user.id)
        access_token = response.session.access_token if response.session else None

        # 3. Instant Access Bypass (Email Verification Override)
        # (This block is now mostly covered by the admin path above, but kept for non-rate-limited standard paths)
        if not access_token:
            if settings.SUPABASE_SERVICE_ROLE_KEY:
                try:
                    from supabase import create_client
                    admin_supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
                    admin_supabase.auth.admin.update_user_by_id(user_id, {"email_confirm": True})
                    log_event(logging.INFO, "user_verification_bypassed", "Email verification bypassed via admin API", user_id=user_id)
                except Exception as e:
                    logger.warning(f"Verification bypass failed: {e}")
            
            try:
                login_resp = supabase.auth.sign_in_with_password({"email": email, "password": user_data.password})
                if login_resp.session:
                    access_token = login_resp.session.access_token
            except:
                pass

        if not access_token:
            # Report the original rate limit error if we still don't have a token
            raise HTTPException(status_code=401, detail="Registration successful, but instant access failed. Please log in manually.")

        # Confirm JWT is valid
        supabase.auth.get_user(access_token)
        log_event(logging.INFO, "registration_complete", "Valid JWT issued", user_id=user_id)
        return TokenResponse(user_id=user_id, email=email, access_token=access_token)

    except HTTPException:
        raise
    except Exception as e:
        err_msg = str(e).lower()
        if "already registered" in err_msg or "user_already_exists" in err_msg:
             raise HTTPException(
                 status_code=400, 
                 detail=f"Registration failed: Email address '{email}' is invalid or already taken"
             )
        
        logger.error(f"Registration failure: {e}")
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """
    Authenticates user and returns a JWT access token.
    """
    email = user_data.email.strip().lower()
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": user_data.password
        })

        if not response.user or not response.session:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        log_event(logging.INFO, "user_logged_in", "User logged in", 
                  user_id=str(response.user.id), email=user_data.email)

        return TokenResponse(
            user_id=str(response.user.id),
            email=str(response.user.email),
            access_token=response.session.access_token
        )
    except Exception as e:
        err_msg = str(e).lower()
        if "invalid login credentials" in err_msg or "invalid_credentials" in err_msg:
             raise HTTPException(status_code=401, detail="Invalid email or password")
        
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed. Please check your credentials.")
