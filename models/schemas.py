from pydantic import BaseModel
from typing import List, Optional, Literal

class MemoryBase(BaseModel):
    content: str
    metadata: Optional[dict] = None
    importance: float = 1.0

class MemoryCreate(MemoryBase):
    pass

class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    metadata: Optional[dict] = None
    importance: Optional[float] = None

class Memory(MemoryBase):
    id: int
    summary: str
    memory_state: Literal["strong", "fading", "resurfaced"] = "strong"
    topics: List[str] = []
    created_at: str
    
    class Config:
        from_attributes = True

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    include_summary: bool = False

class QueryResponse(BaseModel):
    results: List[Memory]
    summary: Optional[str] = None

# --- Auth Schemas ---

class UserRegister(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    user_id: str
    email: str
    access_token: str
