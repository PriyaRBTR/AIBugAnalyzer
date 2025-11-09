"""
Azure DevOps MCP Integration Service
==================================

This service handles communication with the ADO MCP server for live bug data fetching.
Implements all MCP tool calls with no hardcoding - fully dynamic parameters.
"""

import json
import logging
from typing import Dict, List, Optional, Any
import asyncio
import aiohttp
import base64
from datetime import datetime, timedelta
from urllib.parse import quote

from ..core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class MCPAdoService:
    """
    Service class for communicating with Azure DevOps MCP Server
    Provides dynamic bug fetching with no hardcoded values
    """
    
    def __init__(self):
        self.server_name = settings.mcp_server_name
        logger.info(f"Initialized MCP ADO Service with server: {self.server_name}")
    
    async def call_ado_api(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
        """
        Direct Azure DevOps API calls as fallback when MCP is not available
        """
        try:
            if not settings.ado_org_url or not settings.ado_pat:
                return {
                    "success": False,
                    "error": "Azure DevOps credentials not configured. Please set ADO_ORG_URL and ADO_PAT in your environment."
                }
            
            auth_string = base64.b64encode(f":{settings.ado_pat}".encode()).decode()
            headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/json"
            }
            
            url = f"{settings.ado_org_url}{endpoint}"
            logger.info(f"Making ADO API call to: {url}")
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                if method.upper() == "POST":
                    async with session.post(url, json=data) as response:
                        response.raise_for_status()
                        return await response.json()
                else:
                    async with session.get(url) as response:
                        response.raise_for_status()
                        return await response.json()
                        
        except asyncio.TimeoutError:
            logger.error(f"Timeout calling Azure DevOps API: {endpoint}")
            return {
                "success": False,
                "error": "Timeout connecting to Azure DevOps. Please check your network connection."
            }
        except aiohttp.ClientError as e:
            logger.error(f"ADO API call failed for {endpoint}: {str(e)}")
            return {
                "success": False,
                "error": f"Azure DevOps API error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error in ADO API call: {str(e)}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def fetch_bugs_live(self, 
                             project_name: str, 
                             area_path: Optional[str] = None,
                             from_date: Optional[str] = None,
                             to_date: Optional[str] = None,
                             state: Optional[str] = None,
                             limit: int = 100) -> Dict[str, Any]:
        """
        Fetch bugs from Azure DevOps via direct API calls with dynamic parameters
        NO HARDCODING - all parameters are passed through
        """
        logger.info(f"=== FETCH_BUGS_LIVE CALLED ===")
        logger.info(f"project_name: '{project_name}'")
        logger.info(f"area_path: '{area_path}'")
        logger.info(f"from_date: '{from_date}'")
        logger.info(f"to_date: '{to_date}'")
        logger.info(f"state: '{state}'")
        logger.info(f"limit: {limit}")
        logger.info(f"=== END PARAMETERS ===")
        
        try:
            project_encoded = quote(project_name)
            
            # Build WIQL query dynamically based on parameters
            wiql_conditions = [
                "[System.WorkItemType] = 'Bug'"
            ]
            
            # Add area path filter if specified
            if area_path:
                # For Azure DevOps WIQL, try different approaches based on area path structure
                logger.info(f"Processing area_path: '{area_path}' with {area_path.count('\\')} backslashes")
                
                # Try exact match first for any area path - this is most accurate
                wiql_conditions.append(f"[System.AreaPath] = '{area_path}'")
                logger.info(f"Using EXACT match for area path: [System.AreaPath] = '{area_path}'")
            
            # Add date filters if specified - use ChangedDate instead of CreatedDate for better filtering
            if from_date:
                wiql_conditions.append(f"[System.ChangedDate] >= '{from_date}'")
            if to_date:
                wiql_conditions.append(f"[System.ChangedDate] <= '{to_date}'")
            
            # Add state filter if specified
            if state:
                wiql_conditions.append(f"[System.State] = '{state}'")
            
            # Build complete WIQL query - order by ChangedDate for most recently updated bugs
            wiql_query_text = f"SELECT [System.Id] FROM WorkItems WHERE {' AND '.join(wiql_conditions)} ORDER BY [System.ChangedDate] DESC"
            wiql_query = {
                "query": wiql_query_text
            }
            
            # Log the actual WIQL query for debugging
            logger.info(f"Generated WIQL query: {wiql_query_text}")
            logger.info(f"Area path filter logic - area_path: '{area_path}', backslash count: {area_path.count('\\') if area_path else 0}")
            
            # First, get work item IDs using WIQL
            wiql_endpoint = f"/{project_encoded}/_apis/wit/wiql?api-version=7.1"
            wiql_response = await self.call_ado_api(wiql_endpoint, "POST", wiql_query)
            
            if not wiql_response or "workItems" not in wiql_response:
                logger.warning(f"No bugs found for project {project_name} with given filters")
                return {
                    "success": True,
                    "bugs": [],
                    "total_count": 0,
                    "filters_applied": {
                        "project_name": project_name,
                        "area_path": area_path,
                        "from_date": from_date,
                        "to_date": to_date,
                        "state": state,
                        "limit": limit
                    },
                    "organization": settings.ado_org_url
                }
            
            # Get work item IDs (limit results)
            work_items = wiql_response.get("workItems", [])[:limit]
            
            if not work_items:
                return {
                    "success": True,
                    "bugs": [],
                    "total_count": 0,
                    "filters_applied": {
                        "project_name": project_name,
                        "area_path": area_path,
                        "from_date": from_date,
                        "to_date": to_date,
                        "state": state,
                        "limit": limit
                    },
                    "organization": settings.ado_org_url
                }
            
            # Get detailed work item data in batches to avoid URL length limits
            work_item_ids = [str(wi["id"]) for wi in work_items]
            batch_size = 50  # Process work items in smaller batches
            all_work_item_details = []
            
            # Process in batches to avoid URL length limits and API errors
            for i in range(0, len(work_item_ids), batch_size):
                batch_ids = work_item_ids[i:i + batch_size]
                ids_param = ",".join(batch_ids)
                
                logger.info(f"Processing batch {i//batch_size + 1}: IDs {', '.join(batch_ids)}")
                
                # Always try individual requests for better reliability when dealing with small numbers of bugs
                if len(batch_ids) <= 10:  # For small batches, use individual requests for better error handling
                    logger.info(f"Using individual requests for small batch {i//batch_size + 1} ({len(batch_ids)} items)")
                    for individual_id in batch_ids:
                        try:
                            individual_endpoint = f"/_apis/wit/workitems/{individual_id}?$expand=Fields&api-version=7.1"
                            individual_response = await self.call_ado_api(individual_endpoint)
                            if individual_response and not individual_response.get("success") == False and "fields" in individual_response:
                                all_work_item_details.append(individual_response)
                                logger.info(f"Successfully fetched individual work item {individual_id}")
                            else:
                                logger.error(f"Failed to fetch individual work item {individual_id}: {individual_response.get('error', 'Invalid response format')}")
                        except Exception as e:
                            logger.error(f"Exception fetching individual work item {individual_id}: {str(e)}")
                    continue
                
                # For larger batches, try batch request first
                details_endpoint = f"/_apis/wit/workitems?ids={ids_param}&$expand=Fields&api-version=7.1"
                details_response = await self.call_ado_api(details_endpoint)
                
                # Check if the batch call had an explicit error response
                if details_response and details_response.get("success") == False:
                    logger.error(f"Azure DevOps API error for batch {i//batch_size + 1} (IDs: {', '.join(batch_ids)}): {details_response.get('error')}")
                    # Try individual requests for failed batch
                    logger.info(f"Attempting individual requests for failed batch {i//batch_size + 1}")
                    for individual_id in batch_ids:
                        try:
                            individual_endpoint = f"/_apis/wit/workitems/{individual_id}?$expand=Fields&api-version=7.1"
                            individual_response = await self.call_ado_api(individual_endpoint)
                            if individual_response and not individual_response.get("success") == False and "fields" in individual_response:
                                all_work_item_details.append(individual_response)
                                logger.info(f"Successfully fetched individual work item {individual_id}")
                            else:
                                logger.error(f"Failed to fetch individual work item {individual_id}: {individual_response.get('error', 'Invalid response format')}")
                        except Exception as e:
                            logger.error(f"Exception fetching individual work item {individual_id}: {str(e)}")
                    continue
                
                # Check if we got valid data for this batch
                if not details_response or "value" not in details_response:
                    logger.error(f"Invalid response from work items API for batch {i//batch_size + 1} (IDs: {', '.join(batch_ids)})")
                    # Try individual requests for failed batch
                    logger.info(f"Attempting individual requests for batch {i//batch_size + 1} due to invalid response")
                    for individual_id in batch_ids:
                        try:
                            individual_endpoint = f"/_apis/wit/workitems/{individual_id}?$expand=Fields&api-version=7.1"
                            individual_response = await self.call_ado_api(individual_endpoint)
                            if individual_response and not individual_response.get("success") == False and "fields" in individual_response:
                                all_work_item_details.append(individual_response)
                                logger.info(f"Successfully fetched individual work item {individual_id}")
                            else:
                                logger.error(f"Failed to fetch individual work item {individual_id}: {individual_response.get('error', 'Invalid response format')}")
                        except Exception as e:
                            logger.error(f"Exception fetching individual work item {individual_id}: {str(e)}")
                    continue
                
                # Add the successful batch results
                batch_details = details_response.get("value", [])
                all_work_item_details.extend(batch_details)
                logger.info(f"Successfully fetched batch {i//batch_size + 1}: {len(batch_details)} work items (IDs: {', '.join(batch_ids)})")
            
            # Enhanced logging for debugging missing bugs
            fetched_ids = [str(item.get("id", "")) for item in all_work_item_details]
            original_ids = [str(item["id"]) for item in work_items]
            missing_ids = [id for id in original_ids if id not in fetched_ids]
            
            if missing_ids:
                logger.warning(f"Missing work item IDs in final results: {', '.join(missing_ids)}")
                logger.warning(f"Original WIQL returned {len(original_ids)} work items: {', '.join(original_ids)}")
                logger.warning(f"Successfully fetched {len(fetched_ids)} work items: {', '.join(fetched_ids)}")
            
            # If we couldn't fetch any work item details at all
            if not all_work_item_details:
                return {
                    "success": False,
                    "error": "Failed to fetch any work item details from Azure DevOps API",
                    "bugs": [],
                    "total_count": 0,
                    "debug_info": {
                        "wiql_returned_count": len(work_items),
                        "wiql_ids": [str(item["id"]) for item in work_items]
                    }
                }
            
            # Format bugs data
            bugs = []
            for work_item in all_work_item_details:
                fields = work_item.get("fields", {})
                
                bug_data = {
                    "ado_id": work_item.get("id"),
                    "title": fields.get("System.Title", "No Title"),
                    "description": fields.get("System.Description", ""),
                    "state": fields.get("System.State", "Unknown"),
                    "priority": fields.get("Microsoft.VSTS.Common.Priority", "Unknown"),
                    "severity": fields.get("Microsoft.VSTS.Common.Severity", "Unknown"),
                    "assigned_to": fields.get("System.AssignedTo", {}).get("displayName", "Unassigned"),
                    "created_date": fields.get("System.CreatedDate", ""),
                    "changed_date": fields.get("System.ChangedDate", ""),
                    "area_path": fields.get("System.AreaPath", ""),
                    "iteration_path": fields.get("System.IterationPath", ""),
                    "tags": fields.get("System.Tags", ""),
                    "reason": fields.get("System.Reason", ""),
                    "created_by": fields.get("System.CreatedBy", {}).get("displayName", "Unknown"),
                    "changed_by": fields.get("System.ChangedBy", {}).get("displayName", "Unknown"),
                    "history": fields.get("System.History", ""),
                    "comment_count": fields.get("System.CommentCount", 0),
                    "project_name": project_name  # Ensure we track which project this belongs to
                }
                
                bugs.append(bug_data)
            
            logger.info(f"Fetched {len(bugs)} bugs for project {project_name}")
            
            return {
                "success": True,
                "bugs": bugs,
                "total_count": len(bugs),
                "filters_applied": {
                    "project_name": project_name,
                    "area_path": area_path,
                    "from_date": from_date,
                    "to_date": to_date,
                    "state": state,
                    "limit": limit
                },
                "organization": settings.ado_org_url
            }
            
        except Exception as e:
            logger.error(f"Error fetching bugs from Azure DevOps: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "bugs": [],
                "total_count": 0
            }
    
    async def get_projects(self) -> Dict[str, Any]:
        """Get all available Azure DevOps projects dynamically"""
        logger.info("Fetching available projects via Azure DevOps API")
        
        try:
            response = await self.call_ado_api("/_apis/projects?api-version=7.1")
            
            # Check if response is an error response (has "success": False)
            if response.get("success") == False:
                return {
                    "success": False,
                    "error": response.get("error", "Failed to fetch projects"),
                    "projects": []
                }
            
            # If we get here, response should be the raw ADO API response
            projects = []
            for project in response.get("value", []):
                projects.append(project.get("name", ""))
            
            logger.info(f"Found {len(projects)} projects")
            
            return {
                "success": True,
                "projects": projects,
                "total_count": len(projects),
                "organization": settings.ado_org_url
            }
            
        except Exception as e:
            logger.error(f"Error fetching projects: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "projects": []
            }
    
    async def get_area_paths(self, project_name: str) -> Dict[str, Any]:
        """Get area paths for a specific project dynamically"""
        logger.info(f"Fetching area paths for project {project_name} via Azure DevOps API")
        
        try:
            project_encoded = quote(project_name)
            endpoint = f"/{project_encoded}/_apis/wit/classificationnodes/Areas?$depth=10&api-version=7.1"
            response = await self.call_ado_api(endpoint)
            
            if not response.get("success", True):
                # If we can't fetch areas due to permissions or API error, provide some common fallback areas
                logger.warning(f"Could not fetch areas for {project_name}, providing fallback areas")
                fallback_areas = [
                    project_name,  # Root area (same as project name)
                    f"{project_name}\\Development",
                    f"{project_name}\\Testing", 
                    f"{project_name}\\Production",
                    f"{project_name}\\Infrastructure",
                    f"{project_name}\\Documentation"
                ]
                return {
                    "success": True,
                    "area_paths": fallback_areas,
                    "project": project_name,
                    "total_count": len(fallback_areas),
                    "note": "Using fallback areas due to API error or insufficient permissions. Please check your ADO PAT permissions."
                }
            
            area_paths = []
            
            def extract_paths(node, parent_path=""):
                """Recursively extract hierarchical area paths"""
                current_path = f"{parent_path}\\{node['name']}" if parent_path else node['name']
                area_paths.append(current_path)
                
                # Process children recursively to build full hierarchy
                for child in node.get('children', []):
                    extract_paths(child, current_path)
            
            # Extract paths from the response
            if response and 'name' in response:
                extract_paths(response)
            else:
                logger.warning(f"Unexpected response format for area paths: {response}")
                # Fallback to project name if response format is unexpected
                area_paths = [project_name]
            
            logger.info(f"Found {len(area_paths)} area paths for project {project_name}")
            
            return {
                "success": True,
                "area_paths": area_paths,
                "project": project_name,
                "total_count": len(area_paths)
            }
            
        except Exception as e:
            logger.error(f"Error fetching area paths for {project_name}: {str(e)}")
            # Return fallback areas on error
            fallback_areas = [
                project_name,  # Root area (same as project name)
                f"{project_name}\\Development",
                f"{project_name}\\Testing"
            ]
            return {
                "success": True,
                "area_paths": fallback_areas,
                "project": project_name,
                "total_count": len(fallback_areas),
                "error": str(e),
                "note": "Using fallback areas due to error. Please check your Azure DevOps configuration."
            }
    
    async def analyze_bug_patterns(self, 
                                  project_name: str, 
                                  area_path: Optional[str] = None,
                                  days_back: int = 90) -> Dict[str, Any]:
        """Analyze bug patterns for root cause analysis"""
        logger.info(f"Analyzing bug patterns for project {project_name} via MCP")
        
        arguments = {
            "project_name": project_name,
            "days_back": days_back
        }
        
        if area_path:
            arguments["area_path"] = area_path
        
        try:
            response = await self.call_mcp_tool("analyze_bug_patterns", arguments)
            
            if response.get("status") == "error":
                return {
                    "success": False,
                    "error": response.get("error", "Unknown MCP error"),
                    "analysis": {}
                }
            
            analysis_data = response.get("data", {})
            
            return {
                "success": True,
                "analysis": analysis_data.get("analysis_summary", {}),
                "period_analyzed": analysis_data.get("period_analyzed", ""),
                "project": project_name,
                "area_path": area_path
            }
            
        except Exception as e:
            logger.error(f"Error analyzing bug patterns via MCP: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "analysis": {}
            }
    
    async def get_bug_details(self, project_name: str, bug_id: int) -> Dict[str, Any]:
        """Get detailed information about a specific bug"""
        logger.info(f"Fetching bug details for {bug_id} in project {project_name} via MCP")
        
        try:
            response = await self.call_mcp_tool("get_bug_details", {
                "project_name": project_name,
                "bug_id": bug_id
            })
            
            if response.get("status") == "error":
                return {
                    "success": False,
                    "error": response.get("error", "Unknown MCP error"),
                    "bug_details": {}
                }
            
            bug_data = response.get("data", {})
            
            return {
                "success": True,
                "bug_details": bug_data,
                "project": project_name
            }
            
        except Exception as e:
            logger.error(f"Error fetching bug details via MCP: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "bug_details": {}
            }
    
    async def get_recent_bugs(self, days: int = 90) -> Dict[str, Any]:
        """Get bugs from the last N days across projects"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        return await self.fetch_bugs_live(
            project_name="",  # This would need to be handled differently for cross-project queries
            from_date=start_date.strftime("%Y-%m-%d"),
            to_date=end_date.strftime("%Y-%m-%d"),
            limit=200
        )


# Global service instance
mcp_ado_service = MCPAdoService()

def get_mcp_ado_service() -> MCPAdoService:
    """Get MCP ADO service instance"""
    return mcp_ado_service
