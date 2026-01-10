from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    PROJECT_NAME: str = "Second Brain API"
    API_ENV: str = "development"
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None # Optional for local verification
    
    # OpenRouter
    OPENROUTER_API_KEY: str

    # Scaling & Search
    VECTOR_STORE_TYPE: str = "faiss" # Options: "faiss", "supabase"

    def is_production(self) -> bool:
        return self.API_ENV == "production"

settings = Settings()
