"""
Duplicate Detection API endpoints
===============================

This module contains FastAPI endpoints for AI-powered duplicate bug detection,
similarity analysis, and highlighting functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta

from ...services.mcp_ado import get_mcp_ado_service, MCPAdoService
from ...services.ai_service import get_ai_service, AIService
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

class DuplicateSearchRequest(BaseModel):
    """Request model for duplicate search"""
    query_text: str
    project_name: str
    area_path: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    similarity_threshold: Optional[float] = 0.85
    limit: int = 10

class BulkDuplicateRequest(BaseModel):
    """Request model for bulk duplicate detection"""
    bugs: List[Dict[str, Any]]
    similarity_threshold: Optional[float] = 0.85

@router.post("/find-duplicates")
async def find_duplicate_bugs(
    request: DuplicateSearchRequest,
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service),
    ai_service: AIService = Depends(get_ai_service)
) -> Dict[str, Any]:
    """
    Find duplicate bugs using AI-powered semantic similarity
    Returns highlighted matches with similarity scores and explanations
    """
    logger.info(f"POST /find-duplicates - Searching for duplicates of query text")
    
    try:
        # First, fetch existing bugs from the project/area for comparison
        result = await mcp_service.fetch_bugs_live(
            project_name=request.project_name,
            area_path=request.area_path,
            from_date=request.from_date,
            to_date=request.to_date,
            limit=500  # Get more bugs for comprehensive comparison
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch bugs for comparison: {result.get('error', 'Unknown error')}"
            )
        
        existing_bugs = result.get("bugs", [])
        
        if not existing_bugs:
            return {
                "duplicates": [],
                "query_text": request.query_text,
                "total_compared": 0,
                "similarity_threshold": request.similarity_threshold,
                "message": "No existing bugs found in the specified filters",
                "success": True
            }
        
        # Find duplicates using AI service
        duplicates = await ai_service.find_duplicate_bugs(
            query_text=request.query_text,
            existing_bugs=existing_bugs,
            threshold=request.similarity_threshold
        )
        
        # ALSO find bugs that match the search query directly
        query_matches = []
        query_lower = request.query_text.lower()
        for bug in existing_bugs:
            title = bug.get("title", "").lower()
            description = bug.get("description", "").lower()
            if query_lower in title or query_lower in description:
                # Mark as exact query match
                bug_copy = bug.copy()
                bug_copy["similarity_score"] = 100
                bug_copy["match_color"] = "blue"
                bug_copy["match_level"] = "query_match"
                bug_copy["explanation"] = f"Direct match for query '{request.query_text}'"
                query_matches.append(bug_copy)
        
        # Combine results: query matches + duplicates, but avoid duplicates
        all_results = []
        seen_bug_ids = set()
        
        # Add query matches first
        for match in query_matches:
            bug_id = match.get("ado_id")
            if bug_id not in seen_bug_ids:
                all_results.append(match)
                seen_bug_ids.add(bug_id)
        
        # Add duplicates
        for duplicate in duplicates:
            bug_id = duplicate.get("ado_id")
            if bug_id not in seen_bug_ids:
                # Add color coding based on similarity scores
                score = duplicate.get("similarity_score", 0)
                if score >= 95:
                    duplicate["match_color"] = "green"  # 95-100% match
                    duplicate["match_level"] = "exact"
                elif score >= 85:
                    duplicate["match_color"] = "yellow"  # 85-94% match
                    duplicate["match_level"] = "high"
                else:
                    duplicate["match_color"] = "orange"  # Below 85% match
                    duplicate["match_level"] = "moderate"
                
                all_results.append(duplicate)
                seen_bug_ids.add(bug_id)
        
        # Limit results
        all_results = all_results[:request.limit]
        
        return {
            "duplicates": all_results,
            "query_text": request.query_text,
            "total_compared": len(existing_bugs),
            "query_matches_found": len(query_matches),
            "ai_duplicates_found": len(duplicates),
            "total_duplicates_found": len(all_results),
            "similarity_threshold": request.similarity_threshold,
            "filters_applied": result.get("filters_applied", {}),
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in find_duplicate_bugs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/find-duplicates")
async def find_duplicates_get(
    query: str = Query(..., description="Text to search for duplicates"),
    project_name: str = Query(..., description="Azure DevOps project name"),
    area_path: Optional[str] = Query(None, description="Area path filter"),
    from_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    threshold: float = Query(0.85, description="Similarity threshold (0.0-1.0)"),
    limit: int = Query(10, description="Maximum number of duplicates to return"),
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service),
    ai_service: AIService = Depends(get_ai_service)
) -> Dict[str, Any]:
    """
    GET endpoint for duplicate detection - convenient for simple searches
    """
    logger.info(f"GET /find-duplicates - Searching for duplicates via GET")
    
    request = DuplicateSearchRequest(
        query_text=query,
        project_name=project_name,
        area_path=area_path,
        from_date=from_date,
        to_date=to_date,
        similarity_threshold=threshold,
        limit=limit
    )
    
    return await find_duplicate_bugs(request, mcp_service, ai_service)

@router.post("/bulk-duplicate-detection")
async def bulk_duplicate_detection(
    request: BulkDuplicateRequest,
    ai_service: AIService = Depends(get_ai_service)
) -> Dict[str, Any]:
    """
    Detect duplicates within a provided list of bugs
    Useful for analyzing existing bug sets
    """
    logger.info(f"POST /bulk-duplicate-detection - Analyzing {len(request.bugs)} bugs for duplicates")
    
    try:
        duplicate_groups = []
        processed_bugs = set()
        
        for i, bug1 in enumerate(request.bugs):
            if bug1.get("id") in processed_bugs:
                continue
                
            bug1_text = f"{bug1.get('title', '')} {bug1.get('description', '')}"
            similar_bugs = []
            
            # Compare with remaining bugs
            for j, bug2 in enumerate(request.bugs[i+1:], i+1):
                if bug2.get("id") in processed_bugs:
                    continue
                    
                bug2_text = f"{bug2.get('title', '')} {bug2.get('description', '')}"
                
                # Find similarity using AI service
                duplicates = await ai_service.find_duplicate_bugs(
                    query_text=bug1_text,
                    existing_bugs=[bug2],
                    threshold=request.similarity_threshold
                )
                
                if duplicates:
                    similar_bugs.extend(duplicates)
                    processed_bugs.add(bug2.get("id"))
            
            if similar_bugs:
                duplicate_groups.append({
                    "primary_bug": {
                        "id": bug1.get("id"),
                        "ado_id": bug1.get("ado_id"),
                        "title": bug1.get("title"),
                        "created_date": bug1.get("created_date"),
                        "state": bug1.get("state"),
                        "priority": bug1.get("priority")
                    },
                    "similar_bugs": similar_bugs,
                    "group_size": len(similar_bugs) + 1
                })
                processed_bugs.add(bug1.get("id"))
        
        return {
            "duplicate_groups": duplicate_groups,
            "total_bugs_analyzed": len(request.bugs),
            "total_groups_found": len(duplicate_groups),
            "similarity_threshold": request.similarity_threshold,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Error in bulk_duplicate_detection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/similar-bugs/{project_name}/{bug_id}")
async def get_similar_bugs(
    project_name: str,
    bug_id: int,
    limit: int = Query(5, description="Maximum number of similar bugs to return"),
    threshold: float = Query(0.80, description="Similarity threshold"),
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service),
    ai_service: AIService = Depends(get_ai_service)
) -> Dict[str, Any]:
    """
    Find bugs similar to a specific bug by ID
    """
    logger.info(f"GET /similar-bugs/{project_name}/{bug_id} - Finding similar bugs")
    
    try:
        # Get the target bug details
        bug_result = await mcp_service.get_bug_details(project_name, bug_id)
        
        if not bug_result.get("success"):
            raise HTTPException(
                status_code=404,
                detail=f"Bug {bug_id} not found: {bug_result.get('error', 'Unknown error')}"
            )
        
        target_bug = bug_result.get("bug_details", {})
        target_text = f"{target_bug.get('title', '')} {target_bug.get('description', '')}"
        
        # Fetch other bugs from the same project for comparison
        bugs_result = await mcp_service.fetch_bugs_live(
            project_name=project_name,
            limit=300
        )
        
        if not bugs_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch bugs for comparison: {bugs_result.get('error', 'Unknown error')}"
            )
        
        all_bugs = bugs_result.get("bugs", [])
        # Remove the target bug from comparison
        other_bugs = [bug for bug in all_bugs if bug.get("ado_id") != bug_id]
        
        # Find similar bugs
        similar_bugs = await ai_service.find_duplicate_bugs(
            query_text=target_text,
            existing_bugs=other_bugs,
            threshold=threshold
        )
        
        # Limit results
        similar_bugs = similar_bugs[:limit]
        
        return {
            "target_bug": {
                "id": target_bug.get("id"),
                "ado_id": target_bug.get("ado_id"),
                "title": target_bug.get("title"),
                "description": target_bug.get("description", "")[:200] + "..." if len(target_bug.get("description", "")) > 200 else target_bug.get("description", "")
            },
            "similar_bugs": similar_bugs,
            "total_compared": len(other_bugs),
            "similarity_threshold": threshold,
            "project": project_name,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_similar_bugs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/highlight-matches")
async def highlight_text_matches(
    text1: str = Body(..., description="First text to compare"),
    text2: str = Body(..., description="Second text to compare"),
    ai_service: AIService = Depends(get_ai_service)
) -> Dict[str, Any]:
    """
    Utility endpoint to highlight matching text between two pieces of content
    """
    logger.info("POST /highlight-matches - Highlighting text matches")
    
    try:
        # Clean both texts
        cleaned_text1 = ai_service.clean_text(text1)
        cleaned_text2 = ai_service.clean_text(text2)
        
        # Find matching phrases
        matches = ai_service._find_matching_phrases(cleaned_text1, cleaned_text2)
        
        # Extract keywords from both texts
        keywords1 = ai_service.extract_keywords(cleaned_text1)
        keywords2 = ai_service.extract_keywords(cleaned_text2)
        
        # Find common keywords
        common_keywords = list(set(keywords1) & set(keywords2))
        
        return {
            "text1_keywords": keywords1,
            "text2_keywords": keywords2,
            "common_keywords": common_keywords,
            "matching_phrases": matches,
            "match_count": len(matches),
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Error in highlight_text_matches: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/duplicate-statistics")
async def get_duplicate_statistics(
    project_name: str = Query(..., description="Azure DevOps project name"),
    area_path: Optional[str] = Query(None, description="Area path filter"),
    days_back: int = Query(90, description="Number of days to analyze"),
    threshold: float = Query(0.85, description="Similarity threshold for duplicates"),
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service),
    ai_service: AIService = Depends(get_ai_service)
) -> Dict[str, Any]:
    """
    Get statistics about potential duplicates in the project
    """
    logger.info(f"GET /duplicate-statistics - Getting duplicate stats for {project_name}")
    
    try:
        # Fetch bugs for analysis
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        result = await mcp_service.fetch_bugs_live(
            project_name=project_name,
            area_path=area_path,
            from_date=start_date.strftime("%Y-%m-%d"),
            to_date=end_date.strftime("%Y-%m-%d"),
            limit=200  # Limit for performance
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch bugs: {result.get('error', 'Unknown error')}"
            )
        
        bugs = result.get("bugs", [])
        
        if len(bugs) < 2:
            return {
                "statistics": {
                    "total_bugs": len(bugs),
                    "potential_duplicates": 0,
                    "duplicate_rate": 0.0,
                    "most_common_duplicates": []
                },
                "message": "Not enough bugs for duplicate analysis",
                "success": True
            }
        
        # Perform bulk duplicate detection
        bulk_result = await bulk_duplicate_detection(
            BulkDuplicateRequest(bugs=bugs, similarity_threshold=threshold),
            ai_service
        )
        
        duplicate_groups = bulk_result.get("duplicate_groups", [])
        total_duplicates = sum(group["group_size"] - 1 for group in duplicate_groups)
        
        # Calculate statistics
        stats = {
            "total_bugs": len(bugs),
            "potential_duplicate_groups": len(duplicate_groups),
            "total_potential_duplicates": total_duplicates,
            "duplicate_rate": round((total_duplicates / len(bugs)) * 100, 2) if len(bugs) > 0 else 0.0,
            "analysis_period": f"{days_back} days",
            "similarity_threshold": threshold,
            "largest_duplicate_groups": sorted(
                duplicate_groups, 
                key=lambda x: x["group_size"], 
                reverse=True
            )[:5]
        }
        
        return {
            "statistics": stats,
            "project": project_name,
            "area_path": area_path,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_duplicate_statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
