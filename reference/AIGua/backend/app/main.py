from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import app.routers.files as files
import app.routers.config as config
from app.core.config import settings

app = FastAPI(title="Media File Renaming Tool")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8081", "http://127.0.0.1:8081"],  # Vue.js development server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/test")
async def test():
    return {"message": "Test endpoint working"}

# Include routers
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(config.router, prefix="/api/config", tags=["config"])

@app.get("/")
async def root():
    return {"message": "Media File Renaming Tool API"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"} 