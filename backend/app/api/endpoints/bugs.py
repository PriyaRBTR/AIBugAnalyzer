"""
Bug-related API endpoints
========================

This module contains FastAPI endpoints for bug management, fetching, and basic operations.
All endpoints are designed to work dynamically with no hardcoded values.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta

from ...core.database import get_db
from ...services.mcp_ado import get_mcp_ado_service, MCPAdoService
from ...services.ai_service import get_ai_service, AIService
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/projects")
async def get_projects(
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service)
) -> Dict[str, Any]:
    """
    Get all available Azure DevOps projects dynamically
    No hardcoding - fetches live data from MCP server
    """
    logger.info("GET /projects - Fetching available projects")
    
    try:
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
        
    except Exception as e:
        logger.error(f"Error in get_projects: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_name}/areas")
async def get_area_paths(
    project_name: str,
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service)
) -> Dict[str, Any]:
    """
    Get area paths for a specific project dynamically
    """
    logger.info(f"GET /projects/{project_name}/areas - Fetching area paths")
    
    try:
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
        
    except Exception as e:
        logger.error(f"Error in get_area_paths: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bugs")
async def fetch_bugs(
    project_name: str = Query(..., description="Azure DevOps project name"),
    area_path: Optional[str] = Query(None, description="Area path filter"),
    from_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    state: Optional[str] = Query(None, description="Bug state filter"),
    limit: int = Query(100, description="Maximum number of bugs to fetch"),
    recent_days: Optional[int] = Query(None, description="Get bugs from last N days"),
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service)
) -> Dict[str, Any]:
    """
    Fetch bugs with dynamic filtering - NO HARDCODING
    Supports project, area, date range, and state filtering
    """
    logger.info(f"GET /bugs - Fetching bugs for project {project_name}")
    
    try:
        # Handle recent_days filter for quick access
        if recent_days:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=recent_days)
            from_date = start_date.strftime("%Y-%m-%d")
            to_date = end_date.strftime("%Y-%m-%d")
            logger.info(f"Using recent_days filter: {from_date} to {to_date}")
        
        # Make live MCP call with all dynamic parameters
        result = await mcp_service.fetch_bugs_live(
            project_name=project_name,
            area_path=area_path,
            from_date=from_date,
            to_date=to_date,
            state=state,
            limit=limit
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch bugs: {result.get('error', 'Unknown error')}"
            )
        
        bugs = result.get("bugs", [])
        
        # Add summary statistics
        summary = {
            "total_bugs": len(bugs),
            "active_bugs": len([b for b in bugs if b.get("state") not in ["Closed", "Resolved"]]),
            "resolved_bugs": len([b for b in bugs if b.get("state") in ["Closed", "Resolved"]]),
            "high_priority": len([b for b in bugs if "1" in str(b.get("priority", "")) or "High" in str(b.get("priority", ""))]),
            "critical_severity": len([b for b in bugs if "1" in str(b.get("severity", "")) or "Critical" in str(b.get("severity", ""))])
        }
        
        return {
            "bugs": bugs,
            "summary": summary,
            "filters_applied": result.get("filters_applied", {}),
            "organization": result.get("organization", ""),
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Error in fetch_bugs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bugs/{project_name}/{bug_id}")
async def get_bug_details(
    project_name: str,
    bug_id: int,
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service),
    ai_service: AIService = Depends(get_ai_service)
) -> Dict[str, Any]:
    """
    Get detailed information about a specific bug with AI insights
    """
    logger.info(f"GET /bugs/{project_name}/{bug_id} - Fetching bug details")
    
    try:
        # Fetch bug details from MCP
        result = await mcp_service.get_bug_details(project_name, bug_id)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=404 if "not found" in result.get("error", "").lower() else 500,
                detail=result.get("error", "Bug not found")
            )
        
        bug_details = result.get("bug_details", {})
        
        # Generate AI insights
        ai_insights = await ai_service.generate_bug_insights(bug_details)
        
        return {
            "bug_details": bug_details,
            "ai_insights": ai_insights,
            "project": project_name,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_bug_details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bugs/recent")
async def get_recent_bugs(
    days: int = Query(90, description="Number of days to look back"),
    limit: int = Query(100, description="Maximum number of bugs to return"),
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service)
) -> Dict[str, Any]:
    """
    Get recent bugs across projects with quick access
    """
    logger.info(f"GET /bugs/recent - Fetching bugs from last {days} days")
    
    try:
        result = await mcp_service.get_recent_bugs(days)
        
        if not result.get("success"):
            return {
                "message": "Recent bugs endpoint requires specific project selection",
                "suggestion": "Use /bugs endpoint with project_name and recent_days parameters",
                "success": False
            }
        
        return {
            "recent_bugs": result.get("bugs", [])[:limit],
            "days_analyzed": days,
            "total_found": result.get("total_count", 0),
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Error in get_recent_bugs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bugs/patterns")
async def analyze_bug_patterns(
    project_name: str = Query(..., description="Azure DevOps project name"),
    area_path: Optional[str] = Query(None, description="Area path filter"),
    days_back: int = Query(90, description="Number of days to analyze"),
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service)
) -> Dict[str, Any]:
    """
    Analyze bug patterns for insights and trends
    Used for root cause analysis
    """
    logger.info(f"GET /bugs/patterns - Analyzing patterns for project {project_name}")
    
    try:
        result = await mcp_service.analyze_bug_patterns(
            project_name=project_name,
            area_path=area_path,
            days_back=days_back
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to analyze patterns: {result.get('error', 'Unknown error')}"
            )
        
        return {
            "pattern_analysis": result.get("analysis", {}),
            "period_analyzed": result.get("period_analyzed", ""),
            "project": project_name,
            "area_path": area_path,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Error in analyze_bug_patterns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_bug_statistics(
    project_name: str = Query(..., description="Azure DevOps project name"),
    area_path: Optional[str] = Query(None, description="Area path filter"),
    days_back: int = Query(190, description="Number of days for statistics based on last updated date"),
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service)
) -> Dict[str, Any]:
    """
    Get comprehensive bug statistics for dashboard
    Uses last updated date (ChangedDate) instead of created date for better filtering
    """
    logger.info(f"GET /stats - Getting statistics for project {project_name} (last {days_back} days by updated date)")
    
    try:
        # Fetch bugs for statistics using last updated date
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        result = await mcp_service.fetch_bugs_live(
            project_name=project_name,
            area_path=area_path,
            from_date=start_date.strftime("%Y-%m-%d"),
            to_date=end_date.strftime("%Y-%m-%d"),
            limit=1000  # Increased limit for better analysis
        )
        
        if not result.get("success"):
            logger.error(f"Failed to fetch bugs from MCP service: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch statistics: {result.get('error', 'Unknown error')}"
            )
        
        bugs = result.get("bugs", [])
        logger.info(f"Retrieved {len(bugs)} bugs for statistics")
        
        # Calculate comprehensive statistics
        stats = {
            "total_bugs": len(bugs),
            "period": f"Last {days_back} days (by update date)",
            "state_distribution": {},
            "priority_distribution": {},
            "severity_distribution": {},
            "area_distribution": {},
            "assignee_distribution": {},
            "trend_data": []
        }
        
        # Calculate distributions
        for bug in bugs:
            state = bug.get("state", "Unknown")
            stats["state_distribution"][state] = stats["state_distribution"].get(state, 0) + 1
            
            priority = str(bug.get("priority", "Unknown"))
            stats["priority_distribution"][priority] = stats["priority_distribution"].get(priority, 0) + 1
            
            severity = str(bug.get("severity", "Unknown"))
            stats["severity_distribution"][severity] = stats["severity_distribution"].get(severity, 0) + 1
            
            # Shorten area path for display
            area = bug.get("area_path", "Unknown")
            area_short = area.split("\\")[-1] if "\\" in area else area
            stats["area_distribution"][area_short] = stats["area_distribution"].get(area_short, 0) + 1
            
            assignee = bug.get("assigned_to", "Unassigned")
            stats["assignee_distribution"][assignee] = stats["assignee_distribution"].get(assignee, 0) + 1
        
        # Detect duplicates within the bug list with improved algorithm
        duplicates_info = detect_duplicates_in_list(bugs)
        
        return {
            "statistics": stats,
            "bugs": bugs,  # Include the bugs list for display
            "duplicates": duplicates_info,
            "project": project_name,
            "area_path": area_path,
            "filters_applied": result.get("filters_applied", {}),
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_bug_statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def detect_duplicates_in_list(bugs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detect potential duplicate bugs within a list based on title similarity
    """
    from difflib import SequenceMatcher
    
    duplicates = []
    duplicate_groups = {}
    
    for i, bug1 in enumerate(bugs):
        title1 = bug1.get("title", "").lower().strip()
        if not title1:
            continue
            
        matches = []
        
        for j, bug2 in enumerate(bugs):
            if i >= j:  # Avoid comparing with itself and duplicating pairs
                continue
                
            title2 = bug2.get("title", "").lower().strip()
            if not title2:
                continue
            
            # Calculate similarity ratio
            similarity = SequenceMatcher(None, title1, title2).ratio()
            
            if similarity >= 0.75:  # 75% similarity threshold
                matches.append({
                    "bug_id": bug2.get("ado_id"),
                    "title": bug2.get("title"),
                    "similarity": round(similarity * 100, 1),
                    "state": bug2.get("state"),
                    "index": j
                })
        
        if matches:
            duplicate_entry = {
                "primary_bug": {
                    "bug_id": bug1.get("ado_id"), 
                    "title": bug1.get("title"),
                    "state": bug1.get("state"),
                    "index": i
                },
                "similar_bugs": matches,
                "group_size": len(matches) + 1
            }
            
            duplicates.append(duplicate_entry)
            
            # Mark bugs as duplicates in the main list
            for bug in bugs:
                if bug.get("ado_id") == bug1.get("ado_id"):
                    bug["is_duplicate"] = True
                    bug["duplicate_group"] = len(duplicates)
                    
                for match in matches:
                    if bug.get("ado_id") == match["bug_id"]:
                        bug["is_duplicate"] = True
                        bug["duplicate_group"] = len(duplicates)
    
    return {
        "total_duplicates": len(duplicates),
        "duplicate_groups": duplicates,
        "summary": f"Found {len(duplicates)} potential duplicate groups involving {sum(d['group_size'] for d in duplicates)} bugs"
    }
