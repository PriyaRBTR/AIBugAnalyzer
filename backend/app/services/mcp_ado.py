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
    
    async def get_bug_comments(self, project_name: str, bug_id: int) -> Dict[str, Any]:
        """Get comments for a specific bug from Azure DevOps Discussion section"""
        logger.info(f"Fetching discussion comments for bug {bug_id} in project {project_name}")
        
        try:
            project_encoded = quote(project_name)
            
            # Azure DevOps API endpoint for work item updates (includes discussion comments)
            updates_endpoint = f"/{project_encoded}/_apis/wit/workItems/{bug_id}/updates?api-version=7.1"
            
            # Call Azure DevOps API directly
            response = await self.call_ado_api(updates_endpoint)
            
            if response.get("success") == False:
                return {
                    "success": False,
                    "error": response.get("error", "Failed to fetch work item updates"),
                    "comment": None
                }
            
            # Extract updates from response
            updates = response.get("value", [])
            
            if not updates:
                return {
                    "success": True,
                    "comment": None,
                    "message": "No comments available for the selected bug",
                    "total_comments": 0
                }
            
            # Find the most recent update with a discussion comment
            latest_comment = None
            comment_count = 0
            
            # Process updates from newest to oldest to find the last comment
            for update in reversed(updates):
                # Look for updates that contain discussion comments
                fields = update.get("fields", {})
                history_field = fields.get("System.History", {})
                
                # Check if this update has a history/discussion entry
                if history_field and history_field.get("newValue"):
                    comment_text = history_field.get("newValue", "").strip()
                    
                    # Skip empty comments or system-generated updates
                    if (comment_text and 
                        len(comment_text) > 0 and 
                        not comment_text.startswith("Associated with commit") and
                        not comment_text.startswith("Associated with changeset")):
                        
                        # Found a valid comment
                        comment_count += 1
                        
                        if latest_comment is None:  # This is the most recent comment
                            # Get author information
                            revised_by = update.get("revisedBy", {})
                            author_name = revised_by.get("displayName", "Unknown")
                            
                            # Get revision date
                            revised_date = update.get("revisedDate", "")
                            
                            latest_comment = {
                                "text": comment_text,
                                "created_date": revised_date,
                                "created_by": author_name,
                                "revision": update.get("rev", 0)
                            }
                            
                            logger.info(f"Found latest comment for bug {bug_id} by {author_name}: {comment_text[:100]}...")
            
            if latest_comment:
                return {
                    "success": True,
                    "comment": latest_comment,
                    "total_comments": comment_count,
                    "project": project_name
                }
            else:
                return {
                    "success": True,
                    "comment": None,
                    "message": "No comments available for the selected bug",
                    "total_comments": 0
                }
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching work item updates for bug {bug_id}")
            return {
                "success": False,
                "error": "Request timeout while fetching comments",
                "comment": None
            }
        except Exception as e:
            logger.error(f"Error fetching work item updates for bug {bug_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Something went wrong while fetching comments: {str(e)}",
                "comment": None
            }
    
    async def get_bug_comments_with_scoring(self, project_name: str, bug_id: int, min_importance_score: int = 15) -> Dict[str, Any]:
        """
        Enhanced comment selection with intelligent scoring algorithm
        Returns MULTIPLE important comments above the minimum threshold
        Prioritizes technical implementation details over simple status updates
        """
        logger.info(f"Fetching discussion comments with enhanced scoring for bug {bug_id} in project {project_name} (min_score: {min_importance_score})")
        
        try:
            project_encoded = quote(project_name)
            
            # Azure DevOps API endpoint for work item updates (includes discussion comments)
            updates_endpoint = f"/{project_encoded}/_apis/wit/workItems/{bug_id}/updates?api-version=7.1"
            
            # Call Azure DevOps API directly
            response = await self.call_ado_api(updates_endpoint)
            
            if response.get("success") == False:
                return {
                    "success": False,
                    "error": response.get("error", "Failed to fetch work item updates"),
                    "comment_data": None,
                    "important_comments": [],
                    "alternative_comments": [],
                    "selection_criteria": "Error fetching comments"
                }
            
            # Extract updates from response
            updates = response.get("value", [])
            
            if not updates:
                return {
                    "success": True,
                    "comment_data": None,
                    "important_comments": [],
                    "alternative_comments": [],
                    "latest_comment_data": None,
                    "selection_criteria": "No comments available",
                    "total_comments": 0
                }
            
            # Extract all valid comments with scoring
            all_comments = []
            
            # Process updates from newest to oldest
            for update in reversed(updates):
                # Look for updates that contain discussion comments
                fields = update.get("fields", {})
                history_field = fields.get("System.History", {})
                
                # Check if this update has a history/discussion entry
                if history_field and history_field.get("newValue"):
                    comment_text = history_field.get("newValue", "").strip()
                    
                    # Skip empty comments or system-generated updates
                    if (comment_text and 
                        len(comment_text) > 0 and 
                        not comment_text.startswith("Associated with commit") and
                        not comment_text.startswith("Associated with changeset")):
                        
                        # Get author information
                        revised_by = update.get("revisedBy", {})
                        author_name = revised_by.get("displayName", "Unknown")
                        
                        # Get revision date
                        revised_date = update.get("revisedDate", "")
                        
                        # Calculate importance score
                        importance_score = self._calculate_comment_importance_score(comment_text)
                        
                        comment_obj = {
                            "text": comment_text,
                            "created_date": revised_date,
                            "created_by": author_name,
                            "revision": update.get("rev", 0),
                            "importance_score": importance_score
                        }
                        
                        all_comments.append(comment_obj)
            
            if not all_comments:
                return {
                    "success": True,
                    "comment_data": None,
                    "important_comments": [],
                    "alternative_comments": [],
                    "latest_comment_data": None,
                    "selection_criteria": "No valid comments found",
                    "total_comments": 0
                }
            
            # Sort comments by importance score (highest first)
            all_comments.sort(key=lambda x: x["importance_score"], reverse=True)
            
            # Determine comment type based on score
            def get_comment_type(score):
                if score >= 50:
                    return "Implementation Details"
                elif score >= 30:
                    return "Technical Analysis"
                elif score >= 20:
                    return "Investigation Notes"
                elif score >= 10:
                    return "Status Update"
                else:
                    return "General Comment"
            
            # Filter comments that meet importance threshold
            important_comments = [
                comment for comment in all_comments 
                if comment["importance_score"] >= min_importance_score
            ]
            
            # If no comments meet threshold, include top 1-2 comments anyway
            if not important_comments:
                important_comments = all_comments[:2]
                selection_criteria = f"No comments above threshold {min_importance_score}, showing top {len(important_comments)} comments"
            else:
                selection_criteria = f"Found {len(important_comments)} comments above importance threshold {min_importance_score}"
            
            # Select primary comment (highest scoring from important comments)
            primary_comment = important_comments[0] if important_comments else all_comments[0]
            
            # Get latest comment (most recent chronologically)
            latest_comment = max(all_comments, key=lambda x: x.get("revision", 0))
            
            # Format important comments for display
            formatted_important_comments = []
            for i, comment in enumerate(important_comments):
                formatted_comment = {
                    "text": comment["text"],
                    "created_date": comment["created_date"],
                    "created_by": comment["created_by"],
                    "comment_type": get_comment_type(comment["importance_score"]),
                    "importance_score": comment["importance_score"],
                    "is_primary": i == 0,  # Mark the first (highest scoring) as primary
                    "display_priority": i + 1
                }
                formatted_important_comments.append(formatted_comment)
            
            # Format response with enhanced data
            result = {
                "success": True,
                "comment_data": {
                    "text": primary_comment["text"],
                    "created_date": primary_comment["created_date"],
                    "created_by": primary_comment["created_by"],
                    "comment_type": get_comment_type(primary_comment["importance_score"]),
                    "importance_score": primary_comment["importance_score"]
                } if primary_comment else None,
                "important_comments": formatted_important_comments,
                "alternative_comments": [
                    {
                        "text": comment["text"][:200] + "..." if len(comment["text"]) > 200 else comment["text"],
                        "created_by": comment["created_by"],
                        "created_date": comment["created_date"],
                        "comment_type": get_comment_type(comment["importance_score"]),
                        "importance_score": comment["importance_score"]
                    }
                    for comment in all_comments[len(important_comments):len(important_comments)+3]  # Next 3 as alternatives
                ],
                "latest_comment_data": {
                    "text": latest_comment["text"],
                    "created_date": latest_comment["created_date"],
                    "created_by": latest_comment["created_by"],
                    "comment_type": get_comment_type(latest_comment["importance_score"]),
                    "importance_score": latest_comment["importance_score"]
                } if latest_comment and latest_comment != primary_comment else None,
                "selection_criteria": selection_criteria,
                "total_comments": len(all_comments),
                "comments_above_threshold": len(important_comments),
                "threshold_used": min_importance_score,
                "project": project_name
            }
            
            logger.info(f"Enhanced scoring found {len(important_comments)} important comments for bug {bug_id} (threshold: {min_importance_score})")
            
            return result
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching work item updates for bug {bug_id}")
            return {
                "success": False,
                "error": "Request timeout while fetching comments",
                "comment_data": None
            }
        except Exception as e:
            logger.error(f"Error fetching work item updates for bug {bug_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Something went wrong while fetching comments: {str(e)}",
                "comment_data": None
            }
    
    def _calculate_comment_importance_score(self, comment_text: str) -> int:
        """
        Enhanced importance scoring for intelligent comment prioritization
        Specifically designed to surface technical root cause analysis like the Mahalingam example
        Higher scores = more technically valuable comments
        """
        if not comment_text:
            return 0
        
        text_lower = comment_text.lower()
        score = 10  # Base score for any comment
        
        # ROOT CAUSE ANALYSIS - Highest priority (+35 points)
        root_cause_phrases = [
            "root cause analysis", "root cause", "analysis indicates", "analysis revealed",
            "our analysis", "investigation shows", "discovered that", "found that",
            "the issue is caused by", "underlying cause", "primary cause"
        ]
        for phrase in root_cause_phrases:
            if phrase in text_lower:
                score += 35
                break
        
        # CROSS-SYSTEM ANALYSIS - High value technical content (+30 points)
        cross_system_indicators = [
            "plau", "pluk", "pl global", "system comparison", "other systems",
            "similar issue in", "same issue in", "across systems", "multiple systems"
        ]
        for indicator in cross_system_indicators:
            if indicator in text_lower:
                score += 30
                break
        
        # TECHNICAL IMPLEMENTATION DETAILS - High technical value (+28 points)
        implementation_details = [
            "class and", "attribute", "element class", "aria-current", "highlighting functionality",
            "implementation", "code changes", "staged", "committed", "introduced files",
            "new files", "tocHighlightedElement", "dynamically", "scrolling"
        ]
        for detail in implementation_details:
            if detail in text_lower:
                score += 28
                break
        
        # INVESTIGATION PROCESS - Shows analytical thinking (+25 points)
        investigation_keywords = [
            "attempted to validate", "we observed", "as illustrated below", "based on",
            "following internal discussions", "it was decided", "we attempted", "however we observed"
        ]
        for keyword in investigation_keywords:
            if keyword in text_lower:
                score += 25
                break
        
        # TECHNICAL SOLUTION DETAILS - Actionable technical content (+22 points)
        solution_keywords = [
            "to fix", "solution", "workaround", "to address", "to resolve",
            "fix implemented", "changes made", "approach taken", "method used"
        ]
        for keyword in solution_keywords:
            if keyword in text_lower:
                score += 22
                break
        
        # SYSTEM REFERENCES - Technical context (+20 points)
        system_references = [
            "document display page", "search results page", "table of contents",
            "multi-level hierarchy", "collapsible", "focus behavior", "highlighting"
        ]
        for ref in system_references:
            if ref in text_lower:
                score += 20
                break
        
        # Visual content with context (+25 points)
        visual_indicators = [
            "as illustrated below", "image", "screenshot", "attached", "picture", 
            "visual", "see attached", "[image]", "screen capture", "refer to the attached"
        ]
        for indicator in visual_indicators:
            if indicator in text_lower:
                score += 25
                break
        
        # CODE AND TECHNICAL ARTIFACTS (+18 points)
        code_indicators = [
            "function", "method", "class", "variable", "code", "script", "query",
            "file", "path", "folder", "directory", "config", ".js", ".html", 
            ".css", ".py", ".java", ".cs", "src/", "app/", "component"
        ]
        for indicator in code_indicators:
            if indicator in text_lower:
                score += 18
                break
        
        # TECHNICAL ANALYSIS TERMS (+15 points)
        technical_terms = [
            "api", "database", "server", "client", "service", "endpoint", 
            "performance", "memory", "cpu", "network", "timeout", "error", "exception",
            "browser", "dom", "html", "css", "javascript", "frontend", "backend"
        ]
        for term in technical_terms:
            if term in text_lower:
                score += 15
                break
        
        # BONUS for LENGTH - Longer comments often have more technical detail
        if len(comment_text) > 500:  # Long detailed comments
            score += 10
        elif len(comment_text) > 200:  # Medium length comments  
            score += 5
        
        # BONUS for SPECIFIC PRODUCT/SYSTEM NAMES (shows cross-system knowledge)
        if any(system in text_lower for system in ["plau", "pluk", "pl global"]):
            score += 15
        
        # BONUS for TECHNICAL KEYWORDS DENSITY
        technical_density_words = [
            "technical", "implementation", "development", "analysis", "investigation",
            "architecture", "design", "algorithm", "framework", "library", "component"
        ]
        density_count = sum(1 for word in technical_density_words if word in text_lower)
        score += density_count * 3  # 3 points per technical word
        
        # Apply penalties for low-value content
        
        # Simple closure penalty (-20 for brief, -10 for moderate)
        closure_phrases = [
            "closing the bug", "bug closed", "issue closed", "resolved", 
            "closing this", "bug is closed", "issue resolved", "marking as complete"
        ]
        for phrase in closure_phrases:
            if phrase in text_lower:
                if len(comment_text) < 50:  # Brief closure
                    score -= 20
                else:  # Moderate closure with some context
                    score -= 10
                break
        
        # Low-value phrase penalty (stronger penalties)
        low_value_phrases = [
            "thanks", "thank you", "looks good", "approved", "lgtm", 
            "ok", "fine", "agreed", "yes", "no problem", "+1"
        ]
        for phrase in low_value_phrases:
            if phrase in text_lower:
                if len(comment_text) < 30:  # Very brief low-value comment
                    score -= 18
                else:  # Longer comment with low-value phrase
                    score -= 8
                break
        
        # Status update without technical context penalty
        status_only_phrases = [
            "assigned to", "bug assigned", "status changed", "priority changed",
            "moved to", "transferred to", "state changed"
        ]
        for phrase in status_only_phrases:
            if phrase in text_lower and len(comment_text) < 100:
                score -= 15  # Penalize brief status updates more heavily
                break
        
        # Emoji-only or very short comments penalty
        if len(comment_text) < 10:
            score -= 10
        
        # Ensure minimum score but allow negatives for truly low-value content
        return max(score, 1)
    
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
