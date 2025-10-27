"""
Main API Router
==============

This module sets up the main API router that includes all endpoint groups.
"""

from fastapi import APIRouter, HTTPException, Depends

from .endpoints import bugs, duplicates, analytics, collaboration, internal_ai
from ..services.mcp_ado import get_mcp_ado_service, MCPAdoService

# Create main API router
api_router = APIRouter()

# Include all endpoint routers with prefixes
api_router.include_router(
    bugs.router, 
    prefix="/bugs", 
    tags=["bugs"],
    responses={404: {"description": "Not found"}}
)

api_router.include_router(
    duplicates.router, 
    prefix="/duplicates", 
    tags=["duplicates"],
    responses={404: {"description": "Not found"}}
)

api_router.include_router(
    analytics.router, 
    prefix="/analytics", 
    tags=["analytics"],
    responses={404: {"description": "Not found"}}
)

api_router.include_router(
    collaboration.router, 
    prefix="/collaboration", 
    tags=["collaboration"],
    responses={404: {"description": "Not found"}}
)

api_router.include_router(
    internal_ai.router, 
    prefix="/internal-ai", 
    tags=["internal-ai"],
    responses={404: {"description": "Not found"}}
)

# Direct project endpoints (not under /bugs prefix)
@api_router.get("/projects")
async def get_projects(
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service)
):
    """Get all available Azure DevOps projects dynamically"""
    result = await mcp_service.get_projects()
    
    if not result.get("success"):
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch projects: {result.get('error', 'Unknown error')}"
        )
    
    return {
        "projects": result.get("projects", []),
        "total_count": result.get("total_count", 0),
        "organization": result.get("organization", ""),
        "success": True
    }

@api_router.get("/projects/{project_name}/areas")
async def get_area_paths(
    project_name: str,
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service)
):
    """Get area paths for a specific project dynamically"""
    result = await mcp_service.get_area_paths(project_name)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch area paths: {result.get('error', 'Unknown error')}"
        )
    
    return {
        "area_paths": result.get("area_paths", []),
        "project": project_name,
        "total_count": result.get("total_count", 0),
        "success": True
    }

# Health check endpoint
@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "AI Bug Analyzer API is running",
        "version": "1.0.0"
    }
