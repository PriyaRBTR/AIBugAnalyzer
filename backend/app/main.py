"""
AI Bug Analyzer - FastAPI Backend
=================================

Main FastAPI application entry point.
Provides AI-powered duplicate bug analysis integrated with Azure DevOps via MCP.
"""

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from .core.config import get_settings
from .core.database import init_db
from .api.router import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting AI Bug Analyzer Backend...")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
    
    # Log configuration
    logger.info(f"Application: {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"API prefix: {settings.api_v1_prefix}")
    logger.info(f"MCP server: {settings.mcp_server_name}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Bug Analyzer Backend...")

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    AI-powered Duplicate Bug Analyzer integrated with Azure DevOps.
    
    ## Features
    - **Live ADO Integration**: Dynamic bug fetching via MCP server
    - **AI Duplicate Detection**: Semantic similarity analysis with highlighting
    - **Root Cause Analysis**: AI-powered categorization and recommendations
    - **Advanced Analytics**: Trend analysis and quality metrics
    - **No Hardcoding**: Fully dynamic project and area filtering
    
    ## API Endpoints
    - `/api/v1/bugs/*` - Bug management and fetching
    - `/api/v1/duplicates/*` - Duplicate detection and similarity analysis
    - `/api/v1/analytics/*` - Root cause analysis and advanced analytics
    """,
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "success": False
        }
    )

# Include API router with version prefix
app.include_router(api_router, prefix=settings.api_v1_prefix)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with basic information"""
    return {
        "message": "AI Bug Analyzer Backend",
        "version": settings.app_version,
        "description": "AI-powered Duplicate Bug Analyzer with Azure DevOps integration",
        "docs": "/api/v1/docs",
        "health": "/api/v1/health",
        "features": [
            "Live Azure DevOps integration via MCP",
            "AI-powered duplicate detection",
            "Root cause analysis with recommendations",
            "Advanced analytics and trend visualization",
            "Dynamic filtering with no hardcoded values"
        ]
    }

# Additional health check at root level
@app.get("/health")
async def root_health_check():
    """Root level health check"""
    return {
        "status": "healthy",
        "service": "AI Bug Analyzer Backend",
        "version": settings.app_version
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {settings.host}:{settings.port}")
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
