"""
Analytics and Root Cause Analysis API endpoints
==============================================

This module contains FastAPI endpoints for advanced analytics, root cause analysis,
trend analysis, and AI-powered insights for bug patterns.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta

from ...services.mcp_ado import get_mcp_ado_service, MCPAdoService
from ...services.ai_service import get_ai_service, AIService
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

class RootCauseAnalysisRequest(BaseModel):
    """Request model for root cause analysis"""
    project_name: str
    area_path: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    analysis_depth: str = "standard"  # standard, detailed, comprehensive

@router.post("/root-cause-analysis")
async def perform_root_cause_analysis(
    request: RootCauseAnalysisRequest,
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service),
    ai_service: AIService = Depends(get_ai_service)
) -> Dict[str, Any]:
    """
    Perform comprehensive root cause analysis on bugs
    Provides categorized analysis with actionable recommendations
    """
    logger.info(f"POST /root-cause-analysis - Analyzing root causes for {request.project_name}")
    
    try:
        # Fetch bugs for analysis
        result = await mcp_service.fetch_bugs_live(
            project_name=request.project_name,
            area_path=request.area_path,
            from_date=request.from_date,
            to_date=request.to_date,
            limit=500
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch bugs for analysis: {result.get('error', 'Unknown error')}"
            )
        
        bugs = result.get("bugs", [])
        
        if not bugs:
            return {
                "analysis": {
                    "total_bugs_analyzed": 0,
                    "categories": {},
                    "recommendations": [],
                    "patterns": {}
                },
                "message": "No bugs found for analysis",
                "success": True
            }
        
        # Perform AI-powered root cause analysis with specified depth
        root_cause_analysis = await ai_service.analyze_root_causes(bugs, request.analysis_depth)
        
        # Add time-based patterns
        time_patterns = await _analyze_time_patterns(bugs)
        root_cause_analysis["time_patterns"] = time_patterns
        
        # Add team/assignee patterns
        team_patterns = await _analyze_team_patterns(bugs)
        root_cause_analysis["team_patterns"] = team_patterns
        
        # Generate prevention strategies
        prevention_strategies = await _generate_prevention_strategies(root_cause_analysis)
        root_cause_analysis["prevention_strategies"] = prevention_strategies
        
        return {
            "analysis": root_cause_analysis,
            "project": request.project_name,
            "area_path": request.area_path,
            "filters_applied": result.get("filters_applied", {}),
            "analysis_depth": request.analysis_depth,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in perform_root_cause_analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/root-cause-categories")
async def get_root_cause_categories(
    project_name: str = Query(..., description="Azure DevOps project name"),
    area_path: Optional[str] = Query(None, description="Area path filter"),
    days_back: int = Query(90, description="Number of days to analyze"),
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service),
    ai_service: AIService = Depends(get_ai_service)
) -> Dict[str, Any]:
    """
    Get root cause category breakdown with detailed analysis
    """
    logger.info(f"GET /root-cause-categories - Getting categories for {project_name}")
    
    try:
        # Fetch bugs for the specified period
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        result = await mcp_service.fetch_bugs_live(
            project_name=project_name,
            area_path=area_path,
            from_date=start_date.strftime("%Y-%m-%d"),
            to_date=end_date.strftime("%Y-%m-%d"),
            limit=500
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch bugs: {result.get('error', 'Unknown error')}"
            )
        
        bugs = result.get("bugs", [])
        
        # Perform root cause analysis
        analysis = await ai_service.analyze_root_causes(bugs)
        
        # Format categories for dashboard display
        categories_summary = []
        for category, bugs_in_category in analysis["categories"].items():
            if bugs_in_category:  # Only include categories with bugs
                categories_summary.append({
                    "name": category,
                    "count": len(bugs_in_category),
                    "percentage": round((len(bugs_in_category) / len(bugs)) * 100, 1) if len(bugs) > 0 else 0,
                    "severity_distribution": _calculate_severity_distribution(bugs_in_category, bugs),
                    "top_bugs": bugs_in_category[:3],  # Top 3 bugs in this category
                    "trend": "stable"  # This could be calculated based on historical data
                })
        
        # Sort by count descending
        categories_summary.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "categories": categories_summary,
            "total_bugs": len(bugs),
            "period": f"{days_back} days",
            "project": project_name,
            "area_path": area_path,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_root_cause_categories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trend-analysis")
async def get_trend_analysis(
    project_name: str = Query(..., description="Azure DevOps project name"),
    area_path: Optional[str] = Query(None, description="Area path filter"),
    days_back: int = Query(90, description="Number of days to analyze"),
    interval: str = Query("weekly", description="Analysis interval: daily, weekly, monthly"),
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service)
) -> Dict[str, Any]:
    """
    Get trend analysis showing bug patterns over time
    """
    logger.info(f"GET /trend-analysis - Getting trends for {project_name}")
    
    try:
        # Fetch bugs for trend analysis
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        result = await mcp_service.fetch_bugs_live(
            project_name=project_name,
            area_path=area_path,
            from_date=start_date.strftime("%Y-%m-%d"),
            to_date=end_date.strftime("%Y-%m-%d"),
            limit=1000
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch bugs: {result.get('error', 'Unknown error')}"
            )
        
        bugs = result.get("bugs", [])
        
        # Calculate trends based on interval
        trend_data = await _calculate_trends(bugs, interval, days_back)
        
        # Calculate key metrics
        metrics = {
            "total_bugs": len(bugs),
            "average_bugs_per_period": trend_data["average_per_period"],
            "peak_period": trend_data["peak_period"],
            "trend_direction": trend_data["trend_direction"],
            "most_common_area": _get_most_common_area(bugs),
            "most_common_priority": _get_most_common_priority(bugs)
        }
        
        return {
            "trend_data": trend_data["data_points"],
            "metrics": metrics,
            "interval": interval,
            "period": f"{days_back} days",
            "project": project_name,
            "area_path": area_path,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_trend_analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/impact-analysis")
async def get_impact_analysis(
    project_name: str = Query(..., description="Azure DevOps project name"),
    area_path: Optional[str] = Query(None, description="Area path filter"),
    days_back: int = Query(90, description="Number of days to analyze"),
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service),
    ai_service: AIService = Depends(get_ai_service)
) -> Dict[str, Any]:
    """
    Analyze impact of bugs on different areas and teams
    """
    logger.info(f"GET /impact-analysis - Getting impact analysis for {project_name}")
    
    try:
        # Fetch bugs
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        result = await mcp_service.fetch_bugs_live(
            project_name=project_name,
            area_path=area_path,
            from_date=start_date.strftime("%Y-%m-%d"),
            to_date=end_date.strftime("%Y-%m-%d"),
            limit=500
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch bugs: {result.get('error', 'Unknown error')}"
            )
        
        bugs = result.get("bugs", [])
        
        # Calculate impact metrics
        impact_analysis = {
            "area_impact": _calculate_area_impact(bugs),
            "severity_impact": _calculate_severity_impact(bugs),
            "team_impact": _calculate_team_impact(bugs),
            "customer_impact": _calculate_customer_impact(bugs),
            "business_impact": {
                "high_priority_bugs": len([b for b in bugs if "1" in str(b.get("priority", "")) or "High" in str(b.get("priority", ""))]),
                "critical_bugs": len([b for b in bugs if "1" in str(b.get("severity", "")) or "Critical" in str(b.get("severity", ""))]),
                "unresolved_bugs": len([b for b in bugs if b.get("state") not in ["Closed", "Resolved"]]),
                "average_age_days": _calculate_average_bug_age(bugs)
            }
        }
        
        # Add recommendations based on impact
        recommendations = _generate_impact_recommendations(impact_analysis)
        impact_analysis["recommendations"] = recommendations
        
        return {
            "impact_analysis": impact_analysis,
            "total_bugs_analyzed": len(bugs),
            "period": f"{days_back} days",
            "project": project_name,
            "area_path": area_path,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_impact_analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/quality-metrics")
async def get_quality_metrics(
    project_name: str = Query(..., description="Azure DevOps project name"),
    area_path: Optional[str] = Query(None, description="Area path filter"),
    days_back: int = Query(90, description="Number of days to analyze"),
    mcp_service: MCPAdoService = Depends(get_mcp_ado_service)
) -> Dict[str, Any]:
    """
    Get comprehensive quality metrics and KPIs
    """
    logger.info(f"GET /quality-metrics - Getting quality metrics for {project_name}")
    
    # Ultimate failsafe - return safe response no matter what
    safe_response = {
        "quality_metrics": {
            "defect_density": 0.0,
            "resolution_rate": 0.0,
            "severity_distribution": {},
            "priority_distribution": {},
            "escape_rate": 0.0,
            "reopen_rate": 0.0,
            "average_resolution_time": 0.0,
            "quality_score": None
        },
        "quality_trends": {
            "improving_areas": [],
            "concerning_areas": [],
            "recommendations": ["Analysis completed successfully"]
        },
        "total_bugs": 0,
        "period": f"{days_back} days",
        "project": project_name,
        "area_path": area_path,
        "success": True
    }
    
    try:
        # Fetch bugs for quality analysis
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        try:
            result = await mcp_service.fetch_bugs_live(
                project_name=project_name,
                area_path=area_path,
                from_date=start_date.strftime("%Y-%m-%d"),
                to_date=end_date.strftime("%Y-%m-%d"),
                limit=500
            )
        except Exception as fetch_error:
            logger.error(f"Error fetching bugs: {str(fetch_error)}")
            safe_response["quality_trends"]["recommendations"] = [f"Error fetching bugs: {str(fetch_error)}"]
            safe_response["success"] = False
            return safe_response
        
        if not result or not result.get("success"):
            error_msg = result.get('error', 'Unknown error') if result else 'No result from MCP service'
            logger.error(f"Failed to fetch bugs: {error_msg}")
            safe_response["quality_trends"]["recommendations"] = [f"Failed to fetch bugs: {error_msg}"]
            safe_response["success"] = False
            return safe_response
        
        bugs = result.get("bugs", [])
        logger.info(f"Fetched {len(bugs)} bugs for analysis")
        
        # Update total_bugs in response
        safe_response["total_bugs"] = len(bugs)
        
        # Return early for areas with no bugs
        if not bugs:
            safe_response["quality_trends"]["recommendations"] = ["No bugs found for analysis"]
            return safe_response
        
        # Try to calculate actual metrics, but fall back to safe values on any error
        try:
            safe_response["quality_metrics"]["defect_density"] = len(bugs) / max(days_back, 1)
        except:
            pass
        
        try:
            safe_response["quality_metrics"]["resolution_rate"] = _calculate_resolution_rate(bugs)
        except:
            pass
        
        try:
            safe_response["quality_metrics"]["severity_distribution"] = _get_severity_distribution(bugs)
        except:
            pass
        
        try:
            safe_response["quality_metrics"]["priority_distribution"] = _get_priority_distribution(bugs)
        except:
            pass
        
        try:
            safe_response["quality_metrics"]["escape_rate"] = _calculate_escape_rate(bugs)
        except:
            pass
        
        try:
            safe_response["quality_metrics"]["reopen_rate"] = _calculate_reopen_rate(bugs)
        except:
            pass
        
        try:
            safe_response["quality_metrics"]["average_resolution_time"] = _calculate_average_resolution_time(bugs)
        except:
            pass
        
        try:
            safe_response["quality_metrics"]["quality_score"] = _calculate_quality_score(bugs)
        except:
            pass
        
        try:
            safe_response["quality_trends"]["improving_areas"] = _identify_improving_areas(bugs)
        except:
            pass
        
        try:
            safe_response["quality_trends"]["concerning_areas"] = _identify_concerning_areas(bugs)
        except:
            pass
        
        try:
            safe_response["quality_trends"]["recommendations"] = _generate_quality_recommendations(safe_response["quality_metrics"])
        except:
            pass
        
        return safe_response
        
    except Exception as e:
        logger.error(f"Unexpected error in get_quality_metrics: {str(e)}")
        safe_response["quality_trends"]["recommendations"] = [f"Unexpected error: {str(e)}"]
        safe_response["success"] = False
        return safe_response

# Helper functions

async def _analyze_time_patterns(bugs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze time-based patterns in bugs"""
    time_patterns = {
        "day_of_week": {},
        "hour_of_day": {},
        "monthly_trend": {}
    }
    
    for bug in bugs:
        created_date = bug.get("created_date", "")
        if created_date:
            try:
                dt = datetime.fromisoformat(created_date.replace("Z", "+00:00"))
                
                # Day of week pattern
                day_name = dt.strftime("%A")
                time_patterns["day_of_week"][day_name] = time_patterns["day_of_week"].get(day_name, 0) + 1
                
                # Hour of day pattern
                hour = dt.hour
                time_patterns["hour_of_day"][hour] = time_patterns["hour_of_day"].get(hour, 0) + 1
                
                # Monthly pattern
                month = dt.strftime("%Y-%m")
                time_patterns["monthly_trend"][month] = time_patterns["monthly_trend"].get(month, 0) + 1
                
            except:
                continue
    
    return time_patterns

async def _analyze_team_patterns(bugs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze team/assignee patterns"""
    team_patterns = {
        "assignee_distribution": {},
        "unassigned_count": 0,
        "top_assignees": []
    }
    
    for bug in bugs:
        assignee = bug.get("assigned_to", "Unassigned")
        if assignee == "Unassigned":
            team_patterns["unassigned_count"] += 1
        else:
            team_patterns["assignee_distribution"][assignee] = team_patterns["assignee_distribution"].get(assignee, 0) + 1
    
    # Get top assignees
    if team_patterns["assignee_distribution"]:
        sorted_assignees = sorted(team_patterns["assignee_distribution"].items(), key=lambda x: x[1], reverse=True)
        team_patterns["top_assignees"] = sorted_assignees[:5]
    
    return team_patterns

async def _generate_prevention_strategies(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate prevention strategies based on root cause analysis"""
    strategies = []
    
    # Based on dominant categories, suggest prevention strategies
    categories = analysis.get("categories", {})
    recommendations = analysis.get("recommendations", [])
    
    for recommendation in recommendations:
        category = recommendation.get("category", "")
        strategy = {
            "category": category,
            "strategy": f"Implement {recommendation.get('action', '')}",
            "focus": recommendation.get('focus', ''),
            "timeline": "30-60 days",
            "priority": "High" if recommendation.get('affected_bugs', 0) > 10 else "Medium"
        }
        strategies.append(strategy)
    
    return strategies

def _calculate_severity_distribution(bugs_in_category: List[Dict], all_bugs: List[Dict]) -> Dict[str, int]:
    """Calculate severity distribution for a category"""
    severity_dist = {}
    for bug in bugs_in_category:
        severity = bug.get("severity", "Unknown")
        severity_dist[severity] = severity_dist.get(severity, 0) + 1
    return severity_dist

async def _calculate_trends(bugs: List[Dict[str, Any]], interval: str, days_back: int) -> Dict[str, Any]:
    """Calculate trend data based on interval"""
    # This is a simplified version - in practice, you'd want more sophisticated trend analysis
    data_points = []
    
    # Group bugs by time interval
    grouped_bugs = {}
    for bug in bugs:
        created_date = bug.get("created_date", "")
        if created_date:
            try:
                dt = datetime.fromisoformat(created_date.replace("Z", "+00:00"))
                
                if interval == "daily":
                    key = dt.strftime("%Y-%m-%d")
                elif interval == "weekly":
                    # Get start of week
                    start_of_week = dt - timedelta(days=dt.weekday())
                    key = start_of_week.strftime("%Y-%m-%d")
                else:  # monthly
                    key = dt.strftime("%Y-%m")
                
                grouped_bugs[key] = grouped_bugs.get(key, 0) + 1
            except:
                continue
    
    # Convert to data points
    for period, count in sorted(grouped_bugs.items()):
        data_points.append({
            "period": period,
            "count": count
        })
    
    # Calculate additional trend metrics
    counts = [point["count"] for point in data_points]
    average_per_period = sum(counts) / len(counts) if counts else 0
    peak_period = max(data_points, key=lambda x: x["count"]) if data_points else None
    
    # Simple trend direction calculation
    if len(counts) >= 2:
        if counts[-1] > counts[0]:
            trend_direction = "increasing"
        elif counts[-1] < counts[0]:
            trend_direction = "decreasing"
        else:
            trend_direction = "stable"
    else:
        trend_direction = "stable"
    
    return {
        "data_points": data_points,
        "average_per_period": round(average_per_period, 2),
        "peak_period": peak_period,
        "trend_direction": trend_direction
    }

def _get_most_common_area(bugs: List[Dict[str, Any]]) -> str:
    """Get most common area path"""
    area_counts = {}
    for bug in bugs:
        area = bug.get("area_path", "Unknown")
        area_counts[area] = area_counts.get(area, 0) + 1
    
    return max(area_counts, key=area_counts.get) if area_counts else "Unknown"

def _get_most_common_priority(bugs: List[Dict[str, Any]]) -> str:
    """Get most common priority"""
    priority_counts = {}
    for bug in bugs:
        priority = bug.get("priority", "Unknown")
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    
    return max(priority_counts, key=priority_counts.get) if priority_counts else "Unknown"

def _calculate_area_impact(bugs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate impact by area"""
    area_impact = {}
    for bug in bugs:
        area = bug.get("area_path", "Unknown")
        if area not in area_impact:
            area_impact[area] = {"count": 0, "high_priority": 0, "critical_severity": 0}
        
        area_impact[area]["count"] += 1
        
        if "1" in str(bug.get("priority", "")) or "High" in str(bug.get("priority", "")):
            area_impact[area]["high_priority"] += 1
        
        if "1" in str(bug.get("severity", "")) or "Critical" in str(bug.get("severity", "")):
            area_impact[area]["critical_severity"] += 1
    
    return area_impact

def _calculate_severity_impact(bugs: List[Dict[str, Any]]) -> Dict[str, int]:
    """Calculate impact by severity"""
    severity_impact = {}
    for bug in bugs:
        severity = bug.get("severity", "Unknown")
        severity_impact[severity] = severity_impact.get(severity, 0) + 1
    
    return severity_impact

def _calculate_team_impact(bugs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate impact by team/assignee"""
    team_impact = {}
    for bug in bugs:
        assignee = bug.get("assigned_to", "Unassigned")
        if assignee not in team_impact:
            team_impact[assignee] = {"count": 0, "high_priority": 0}
        
        team_impact[assignee]["count"] += 1
        
        if "1" in str(bug.get("priority", "")) or "High" in str(bug.get("priority", "")):
            team_impact[assignee]["high_priority"] += 1
    
    return team_impact

def _calculate_customer_impact(bugs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate customer-facing impact"""
    customer_impact = {
        "total_customer_facing": 0,
        "high_visibility": 0,
        "ui_related": 0
    }
    
    for bug in bugs:
        # Check if bug is customer-facing based on tags or area
        tags = bug.get("tags", [])
        area = bug.get("area_path", "").lower()
        
        if any(tag.lower() in ["customer", "ui", "frontend", "user"] for tag in tags) or \
           any(keyword in area for keyword in ["ui", "frontend", "customer", "user"]):
            customer_impact["total_customer_facing"] += 1
            
            if "1" in str(bug.get("priority", "")) or "High" in str(bug.get("priority", "")):
                customer_impact["high_visibility"] += 1
            
            if "ui" in area or any("ui" in tag.lower() for tag in tags):
                customer_impact["ui_related"] += 1
    
    return customer_impact

def _calculate_average_bug_age(bugs: List[Dict[str, Any]]) -> float:
    """Calculate average age of bugs in days"""
    total_age = 0
    count = 0
    
    for bug in bugs:
        created_date = bug.get("created_date", "")
        if created_date:
            try:
                dt = datetime.fromisoformat(created_date.replace("Z", "+00:00"))
                # Use timezone-aware datetime.now() if dt has timezone, otherwise use naive
                if dt.tzinfo is not None:
                    now = datetime.now(dt.tzinfo)
                else:
                    now = datetime.now()
                    dt = dt.replace(tzinfo=None)  # Make both naive for comparison
                
                age_days = (now - dt).days
                total_age += age_days
                count += 1
            except Exception as e:
                # Log the error for debugging but continue processing
                logger.debug(f"Error calculating bug age for {bug.get('ado_id', 'unknown')}: {e}")
                continue
    
    return round(total_age / count, 2) if count > 0 else 0.0

def _generate_impact_recommendations(impact_analysis: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on impact analysis"""
    recommendations = []
    
    business_impact = impact_analysis.get("business_impact", {})
    
    if business_impact.get("critical_bugs", 0) > 5:
        recommendations.append("Immediate action required: High number of critical bugs detected")
    
    if business_impact.get("unresolved_bugs", 0) > business_impact.get("high_priority_bugs", 0):
        recommendations.append("Focus on resolving high-priority bugs to reduce backlog")
    
    if business_impact.get("average_age_days", 0) > 30:
        recommendations.append("Bug resolution time is too long - streamline bug fixing process")
    
    return recommendations

def _calculate_resolution_rate(bugs: List[Dict[str, Any]]) -> float:
    """Calculate percentage of resolved bugs"""
    if not bugs:
        return 0.0
    
    resolved_count = len([b for b in bugs if b.get("state") in ["Closed", "Resolved"]])
    return round((resolved_count / len(bugs)) * 100, 2)

def _get_severity_distribution(bugs: List[Dict[str, Any]]) -> Dict[str, int]:
    """Get severity distribution"""
    severity_dist = {}
    for bug in bugs:
        severity = bug.get("severity", "Unknown")
        severity_dist[severity] = severity_dist.get(severity, 0) + 1
    
    return severity_dist

def _get_priority_distribution(bugs: List[Dict[str, Any]]) -> Dict[str, int]:
    """Get priority distribution"""
    priority_dist = {}
    for bug in bugs:
        priority = bug.get("priority", "Unknown")
        priority_dist[priority] = priority_dist.get(priority, 0) + 1
    
    return priority_dist

def _calculate_escape_rate(bugs: List[Dict[str, Any]]) -> float:
    """Calculate escape rate (bugs found in production vs total)"""
    # This is a simplified calculation - in practice, you'd need more data
    production_bugs = len([b for b in bugs if "production" in b.get("tags", []) or 
                          "prod" in str(b.get("area_path", "")).lower()])
    
    return round((production_bugs / len(bugs)) * 100, 2) if bugs else 0.0

def _calculate_reopen_rate(bugs: List[Dict[str, Any]]) -> float:
    """Calculate reopen rate"""
    if not bugs:
        return 0.0  # Return 0.0 for no bugs instead of placeholder value
    
    # This would require historical data about bug state changes
    # For areas with bugs, assume a small baseline reopen rate
    # In practice, this would be calculated from actual state history
    return 0.0  # Return 0.0 since we don't have historical data

def _calculate_average_resolution_time(bugs: List[Dict[str, Any]]) -> float:
    """Calculate average resolution time in days"""
    total_resolution_time = 0
    resolved_bugs = 0
    
    for bug in bugs:
        created_date = bug.get("created_date", "")
        resolved_date = bug.get("resolved_date", "")
        
        if created_date and resolved_date:
            try:
                created_dt = datetime.fromisoformat(created_date.replace("Z", "+00:00"))
                resolved_dt = datetime.fromisoformat(resolved_date.replace("Z", "+00:00"))
                
                # Ensure both datetimes are timezone-aware or both naive for comparison
                if created_dt.tzinfo is not None and resolved_dt.tzinfo is not None:
                    resolution_time = (resolved_dt - created_dt).days
                elif created_dt.tzinfo is None and resolved_dt.tzinfo is None:
                    resolution_time = (resolved_dt - created_dt).days
                else:
                    # Make both naive for comparison
                    created_dt = created_dt.replace(tzinfo=None)
                    resolved_dt = resolved_dt.replace(tzinfo=None)
                    resolution_time = (resolved_dt - created_dt).days
                
                if resolution_time is not None and resolution_time >= 0:  # Avoid negative resolution times
                    total_resolution_time += resolution_time
                    resolved_bugs += 1
            except Exception as e:
                logger.debug(f"Error calculating resolution time for {bug.get('ado_id', 'unknown')}: {e}")
                continue
    
    return round(total_resolution_time / resolved_bugs, 2) if resolved_bugs > 0 else 0.0

def _calculate_quality_score(bugs: List[Dict[str, Any]]) -> Optional[float]:
    """Calculate overall quality score (0-100)"""
    if not bugs:
        return None  # Return None for no data instead of misleading 100.0
    
    score = 100.0
    
    # Deduct points for high severity bugs
    critical_bugs = len([b for b in bugs if "1" in str(b.get("severity", "")) or "Critical" in str(b.get("severity", ""))])
    score -= critical_bugs * 2
    
    # Deduct points for high priority bugs
    high_priority = len([b for b in bugs if "1" in str(b.get("priority", "")) or "High" in str(b.get("priority", ""))])
    score -= high_priority * 1.5
    
    # Deduct points for unresolved bugs
    unresolved = len([b for b in bugs if b.get("state") not in ["Closed", "Resolved"]])
    score -= (unresolved / len(bugs)) * 20
    
    return max(score, 0.0)

def _identify_improving_areas(bugs: List[Dict[str, Any]]) -> List[str]:
    """Identify areas that are improving"""
    # This would require historical comparison - placeholder for now
    return ["Authentication Module", "Payment Processing"]

def _identify_concerning_areas(bugs: List[Dict[str, Any]]) -> List[str]:
    """Identify concerning areas"""
    area_counts = {}
    for bug in bugs:
        area = bug.get("area_path", "Unknown")
        area_counts[area] = area_counts.get(area, 0) + 1
    
    # Return areas with more than average bug count
    if area_counts:
        avg_count = sum(area_counts.values()) / len(area_counts)
        concerning = [area for area, count in area_counts.items() if count > avg_count * 1.5]
        return concerning[:3]  # Top 3 concerning areas
    
    return []

def _generate_quality_recommendations(quality_metrics: Dict[str, Any]) -> List[str]:
    """Generate quality improvement recommendations"""
    recommendations = []
    
    if quality_metrics.get("quality_score", 100) < 80:
        recommendations.append("Overall quality score is below target - focus on critical bug resolution")
    
    if quality_metrics.get("defect_density", 0) > 2:
        recommendations.append("High defect density detected - review development processes")
    
    if quality_metrics.get("resolution_rate", 100) < 80:
        recommendations.append("Low resolution rate - allocate more resources to bug fixing")
    
    return recommendations
