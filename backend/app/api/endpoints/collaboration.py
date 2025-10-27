"""
Collaboration and Export API endpoints
=====================================

Endpoints for team collaboration features including bug review status,
comments, and export functionality for duplicate findings and analysis results.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
import json
import csv
import io
from datetime import datetime

from ...services.mcp_ado import MCPAdoService, get_mcp_ado_service
from ...services.ai_service import AIService, get_ai_service

router = APIRouter(prefix="/collaboration", tags=["collaboration"])

# Pydantic models for request/response
class BugReviewStatus(BaseModel):
    bug_id: str
    status: str  # "reviewed", "ignored", "valid", "duplicate"
    reviewer: str
    review_date: str
    notes: Optional[str] = None

class ExportRequest(BaseModel):
    project_name: str
    area_path: Optional[str] = None
    export_type: str  # "duplicates", "root_cause", "analytics", "all"
    format: str  # "csv", "json"
    include_analysis: bool = True
    date_range_days: Optional[int] = 30

class DuplicateReviewRequest(BaseModel):
    query_text: str
    project_name: str
    area_path: Optional[str] = None
    duplicate_id: str
    status: str  # "confirmed", "rejected", "needs_review"
    reviewer: str
    notes: Optional[str] = None

# Initialize services
mcp_ado_service = get_mcp_ado_service()
ai_service = get_ai_service()

@router.post("/review-duplicate")
async def review_duplicate(review_data: DuplicateReviewRequest):
    """
    Mark a duplicate bug finding as reviewed with status
    """
    try:
        # In a real implementation, this would store the review in a database
        # For now, we'll return a confirmation
        review_record = {
            "id": f"review_{review_data.duplicate_id}_{datetime.now().isoformat()}",
            "duplicate_id": review_data.duplicate_id,
            "status": review_data.status,
            "reviewer": review_data.reviewer,
            "review_date": datetime.now().isoformat(),
            "notes": review_data.notes,
            "query_text": review_data.query_text,
            "project": review_data.project_name,
            "area": review_data.area_path
        }
        
        return {
            "success": True,
            "message": f"Duplicate review recorded with status: {review_data.status}",
            "review_record": review_record
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record review: {str(e)}")

@router.get("/review-history")
async def get_review_history(
    project_name: str = Query(..., description="Project name"),
    area_path: Optional[str] = Query(None, description="Area path filter"),
    reviewer: Optional[str] = Query(None, description="Filter by reviewer"),
    status: Optional[str] = Query(None, description="Filter by review status"),
    days_back: int = Query(30, description="Days to look back")
):
    """
    Get history of duplicate reviews and team collaboration
    """
    try:
        # In a real implementation, this would fetch from database
        # For demo purposes, return sample data
        sample_reviews = [
            {
                "id": "review_001",
                "duplicate_id": "12345",
                "bug_title": "Login timeout error on Chrome",
                "status": "confirmed",
                "reviewer": "john.doe@company.com",
                "review_date": "2024-10-20T10:30:00Z",
                "notes": "Confirmed duplicate of existing authentication issue #67890",
                "project": project_name,
                "area": area_path or "Authentication"
            },
            {
                "id": "review_002", 
                "duplicate_id": "12346",
                "bug_title": "Search results not loading",
                "status": "rejected",
                "reviewer": "jane.smith@company.com",
                "review_date": "2024-10-19T15:45:00Z",
                "notes": "Different root cause - this is API timeout, original was UI rendering issue",
                "project": project_name,
                "area": area_path or "Search"
            }
        ]
        
        # Apply filters
        filtered_reviews = sample_reviews
        if reviewer:
            filtered_reviews = [r for r in filtered_reviews if reviewer.lower() in r["reviewer"].lower()]
        if status:
            filtered_reviews = [r for r in filtered_reviews if r["status"] == status]
            
        return {
            "success": True,
            "reviews": filtered_reviews,
            "total_count": len(filtered_reviews),
            "filters_applied": {
                "project": project_name,
                "area": area_path,
                "reviewer": reviewer,
                "status": status,
                "days_back": days_back
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get review history: {str(e)}")

@router.post("/export-analysis")
async def export_analysis(export_request: ExportRequest, background_tasks: BackgroundTasks):
    """
    Export duplicate findings and analysis results
    """
    try:
        # Get the data based on export type
        export_data = {}
        
        if export_request.export_type in ["duplicates", "all"]:
            # Get recent duplicate analyses (mock data for demo)
            export_data["duplicates"] = {
                "summary": {
                    "total_analyzed": 150,
                    "duplicates_found": 23,
                    "avg_similarity_score": 87.5,
                    "export_date": datetime.now().isoformat()
                },
                "findings": [
                    {
                        "original_query": "User login fails with timeout",
                        "duplicate_bug_id": "12345",
                        "duplicate_title": "Authentication timeout in Chrome browser",
                        "similarity_score": 92.3,
                        "explanation": "Both describe login timeout issues with similar symptoms",
                        "status": "confirmed"
                    },
                    {
                        "original_query": "Search not returning results",
                        "duplicate_bug_id": "12346", 
                        "duplicate_title": "Search functionality broken after update",
                        "similarity_score": 89.1,
                        "explanation": "Similar search functionality issues post-deployment",
                        "status": "needs_review"
                    }
                ]
            }
        
        if export_request.export_type in ["root_cause", "all"]:
            export_data["root_cause_analysis"] = {
                "summary": {
                    "total_bugs_analyzed": 200,
                    "categories_identified": 8,
                    "top_category": "UI/Frontend Issues",
                    "analysis_date": datetime.now().isoformat()
                },
                "categories": {
                    "UI/Frontend Issues": {
                        "count": 45,
                        "percentage": 22.5,
                        "common_symptoms": ["rendering issues", "responsive design problems", "JavaScript errors"]
                    },
                    "API/Backend Issues": {
                        "count": 38,
                        "percentage": 19.0,
                        "common_symptoms": ["timeout errors", "500 status codes", "database connection issues"]
                    }
                },
                "recommendations": [
                    {
                        "category": "UI/Frontend Issues",
                        "focus": "Strengthen cross-browser testing",
                        "action": "Implement automated UI testing pipeline",
                        "timeline": "2 weeks"
                    }
                ]
            }
        
        if export_request.export_type in ["analytics", "all"]:
            export_data["analytics"] = {
                "quality_metrics": {
                    "quality_score": 78.5,
                    "resolution_rate": 85.2,
                    "average_resolution_time": 3.4,
                    "escape_rate": 12.1
                },
                "trends": {
                    "trend_direction": "improving",
                    "monthly_bug_count": [45, 38, 42, 35],
                    "resolution_time_trend": "decreasing"
                }
            }
        
        # Format data based on requested format
        if export_request.format == "csv":
            return await export_to_csv(export_data, export_request.export_type)
        else:
            return {
                "success": True,
                "export_format": "json",
                "export_type": export_request.export_type,
                "data": export_data,
                "metadata": {
                    "export_date": datetime.now().isoformat(),
                    "project": export_request.project_name,
                    "area": export_request.area_path,
                    "date_range_days": export_request.date_range_days
                }
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export analysis: {str(e)}")

async def export_to_csv(export_data: dict, export_type: str) -> dict:
    """Convert export data to CSV format"""
    csv_files = {}
    
    try:
        if "duplicates" in export_data:
            # Create CSV for duplicates
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            writer.writerow([
                "Original Query", "Duplicate Bug ID", "Duplicate Title", 
                "Similarity Score", "Explanation", "Status"
            ])
            
            # Write data
            for finding in export_data["duplicates"]["findings"]:
                writer.writerow([
                    finding["original_query"],
                    finding["duplicate_bug_id"],
                    finding["duplicate_title"],
                    finding["similarity_score"],
                    finding["explanation"],
                    finding["status"]
                ])
            
            csv_files["duplicates.csv"] = output.getvalue()
            output.close()
        
        if "root_cause_analysis" in export_data:
            # Create CSV for root cause analysis
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            writer.writerow(["Category", "Bug Count", "Percentage", "Common Symptoms"])
            
            # Write data
            for category, data in export_data["root_cause_analysis"]["categories"].items():
                writer.writerow([
                    category,
                    data["count"],
                    data["percentage"],
                    "; ".join(data["common_symptoms"])
                ])
            
            csv_files["root_cause_analysis.csv"] = output.getvalue()
            output.close()
        
        return {
            "success": True,
            "export_format": "csv",
            "files": csv_files,
            "download_instructions": "Use the file contents to create CSV files locally"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create CSV export: {str(e)}")

@router.get("/team-stats")
async def get_team_collaboration_stats(
    project_name: str = Query(..., description="Project name"),
    area_path: Optional[str] = Query(None, description="Area path filter"),
    days_back: int = Query(30, description="Days to analyze")
):
    """
    Get team collaboration statistics and duplicate review metrics
    """
    try:
        # In a real implementation, this would query database for actual stats
        team_stats = {
            "review_activity": {
                "total_reviews": 45,
                "confirmed_duplicates": 28,
                "rejected_duplicates": 12,
                "pending_reviews": 5,
                "avg_review_time_hours": 2.3
            },
            "reviewer_stats": [
                {
                    "reviewer": "john.doe@company.com",
                    "reviews_completed": 18,
                    "accuracy_score": 92.5,
                    "avg_review_time_hours": 1.8
                },
                {
                    "reviewer": "jane.smith@company.com", 
                    "reviews_completed": 15,
                    "accuracy_score": 89.2,
                    "avg_review_time_hours": 2.1
                },
                {
                    "reviewer": "mike.johnson@company.com",
                    "reviews_completed": 12,
                    "accuracy_score": 94.1,
                    "avg_review_time_hours": 2.8
                }
            ],
            "duplicate_trends": {
                "weekly_duplicate_rate": [15, 12, 18, 14],
                "common_duplicate_categories": [
                    {"category": "Authentication", "count": 8},
                    {"category": "UI/UX", "count": 6},
                    {"category": "Performance", "count": 5}
                ],
                "false_positive_rate": 15.2
            },
            "quality_impact": {
                "bugs_prevented_from_duplication": 23,
                "estimated_time_saved_hours": 46.5,
                "team_efficiency_improvement": "18%"
            }
        }
        
        return {
            "success": True,
            "team_stats": team_stats,
            "analysis_period": {
                "project": project_name,
                "area": area_path,
                "days_back": days_back,
                "period_end": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get team stats: {str(e)}")
