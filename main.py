from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from api.routes import router as api_router
from api.auth import router as auth_router

# Load environment variables
load_dotenv()

app = FastAPI(title="Second Brain API")

# Configure CORS for Local Development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, this should be specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(api_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Second Brain API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
