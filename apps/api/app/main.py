"""
Prism API Backend
Main application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
import os

# Add project root to path to import existing modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from apps.api.app.api import projects, workflows, query, indexes, auth, pipeline, rollback, chat, evaluation, storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup/shutdown events"""
    # Startup
    print("Prism API starting...")
    yield
    # Shutdown
    print("Prism API shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Prism API",
    description="Backend API for document processing and knowledge querying",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["Workflows"])
app.include_router(query.router, prefix="/api/query", tags=["Query"])
app.include_router(indexes.router, prefix="/api/indexes", tags=["Indexes"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["Pipeline"])
app.include_router(rollback.router, prefix="/api/rollback", tags=["Rollback"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(evaluation.router, prefix="/api/evaluation", tags=["Evaluation"])
app.include_router(storage.router, prefix="/api/storage", tags=["Storage"])


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "status": "healthy",
        "service": "Prism API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
