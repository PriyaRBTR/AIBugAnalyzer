#!/usr/bin/env python3
"""
AI Bug Analyzer MCP Server for Azure DevOps Integration
=====================================================

This MCP server provides specialized tools for AI-powered bug analysis:
- Dynamic project and area filtering
- Live bug fetching with date range support
- Duplicate detection capabilities
- Root cause analysis endpoints
- Trend analysis and insights

Features:
- Zero hardcoding - all parameters are dynamic
- Real-time ADO integration via REST API
- Specialized endpoints for bug analysis
- Comprehensive error handling and logging
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import requests
import base64
from urllib.parse import quote
from dotenv import load_dotenv
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import Resource, Tool, TextContent, ImageContent, EmbeddedResource
import mcp.types as types

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Azure DevOps API configuration - no hardcoding
ADO_ORG_URL = os.getenv("ADO_ORG_URL")
ADO_PAT = os.getenv("ADO_PAT")

class AdoBugAnalyzerMCPServer:
    """Azure DevOps MCP Server specialized for AI bug analysis"""
    
    def __init__(self):
        self.server = Server("ado-bug-analyzer")
        self.session = requests.Session()
        
        if ADO_PAT:
            # Encode PAT for basic auth
            auth_string = base64.b64encode(f":{ADO_PAT}".encode()).decode()
            self.session.headers.update({
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/json"
            })
            logger.info("ADO authentication configured successfully")
        else:
            logger.warning("ADO_PAT not found in environment variables")
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up MCP server handlers for bug analysis"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> list[Resource]:
            """List available ADO bug analysis resources"""
            return [
                Resource(
                    uri="ado://projects/list",
                    name="Available Projects",
                    description="List all available Azure DevOps projects",
                    mimeType="application/json"
                ),
                Resource(
                    uri="ado://areas/list",
                    name="Area Paths",
                    description="Get area paths for a specific project",
                    mimeType="application/json"
                ),
                Resource(
                    uri="ado://bugs/recent",
                    name="Recent Bugs",
                    description="Recently created or updated bugs",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read ADO resource data dynamically"""
            if uri.startswith("ado://"):
                resource_type = uri.split("/")[-1]
                
                if resource_type == "list" and "projects" in uri:
                    return await self._get_projects()
                elif resource_type == "recent" and "bugs" in uri:
                    return await self._get_recent_bugs()
            
            raise ValueError(f"Unknown resource: {uri}")
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """List available ADO bug analysis tools"""
            return [
                Tool(
                    name="fetch_bugs",
                    description="Fetch bugs dynamically with project, area, and date filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_name": {
                                "type": "string",
                                "description": "Azure DevOps project name"
                            },
                            "area_path": {
                                "type": "string",
                                "description": "Area path filter (optional)",
                                "default": ""
                            },
                            "from_date": {
                                "type": "string",
                                "description": "Start date filter (YYYY-MM-DD format, optional)"
                            },
                            "to_date": {
                                "type": "string",
                                "description": "End date filter (YYYY-MM-DD format, optional)"
                            },
                            "work_item_type": {
                                "type": "string",
                                "enum": ["Bug", "all"],
                                "default": "Bug",
                                "description": "Filter by work item type"
                            },
                            "state": {
                                "type": "string",
                                "description": "Bug state filter (Active, Resolved, Closed, etc.)"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 100,
                                "description": "Maximum number of bugs to fetch"
                            }
                        },
                        "required": ["project_name"]
                    }
                ),
                Tool(
                    name="get_projects",
                    description="Get list of all available Azure DevOps projects",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_area_paths",
                    description="Get area paths for a specific project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_name": {
                                "type": "string",
                                "description": "Azure DevOps project name"
                            }
                        },
                        "required": ["project_name"]
                    }
                ),
                Tool(
                    name="analyze_bug_patterns",
                    description="Analyze bugs for patterns and potential root causes",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_name": {
                                "type": "string",
                                "description": "Azure DevOps project name"
                            },
                            "area_path": {
                                "type": "string",
                                "description": "Area path filter (optional)"
                            },
                            "days_back": {
                                "type": "integer",
                                "default": 90,
                                "description": "Number of days to analyze"
                            }
                        },
                        "required": ["project_name"]
                    }
                ),
                Tool(
                    name="get_bug_details",
                    description="Get detailed information about a specific bug",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_name": {
                                "type": "string",
                                "description": "Azure DevOps project name"
                            },
                            "bug_id": {
                                "type": "integer",
                                "description": "Bug work item ID"
                            }
                        },
                        "required": ["project_name", "bug_id"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            """Handle tool calls for bug analysis"""
            logger.info(f"Handling tool call: {name} with arguments: {arguments}")
            
            if name == "fetch_bugs":
                result = await self._fetch_bugs(
                    project_name=arguments["project_name"],
                    area_path=arguments.get("area_path", ""),
                    from_date=arguments.get("from_date"),
                    to_date=arguments.get("to_date"),
                    work_item_type=arguments.get("work_item_type", "Bug"),
                    state=arguments.get("state"),
                    limit=arguments.get("limit", 100)
                )
                return [types.TextContent(type="text", text=result)]
            
            elif name == "get_projects":
                result = await self._get_projects()
                return [types.TextContent(type="text", text=result)]
            
            elif name == "get_area_paths":
                result = await self._get_area_paths(
                    project_name=arguments["project_name"]
                )
                return [types.TextContent(type="text", text=result)]
            
            elif name == "analyze_bug_patterns":
                result = await self._analyze_bug_patterns(
                    project_name=arguments["project_name"],
                    area_path=arguments.get("area_path", ""),
                    days_back=arguments.get("days_back", 90)
                )
                return [types.TextContent(type="text", text=result)]
            
            elif name == "get_bug_details":
                result = await self._get_bug_details(
                    project_name=arguments["project_name"],
                    bug_id=arguments["bug_id"]
                )
                return [types.TextContent(type="text", text=result)]
            
            raise ValueError(f"Unknown tool: {name}")
    
    async def _fetch_bugs(self, project_name: str, area_path: str = "", 
                         from_date: Optional[str] = None, to_date: Optional[str] = None,
                         work_item_type: str = "Bug", state: Optional[str] = None,
                         limit: int = 100) -> str:
        """Fetch bugs with dynamic filtering - NO HARDCODING"""
        try:
            if not ADO_PAT or not ADO_ORG_URL:
                return json.dumps({"error": "ADO_PAT or ADO_ORG_URL not configured. Please set your Azure DevOps credentials."})

            logger.info(f"Making live MCP call for project {project_name}, area {area_path}")
            
            project_encoded = quote(project_name)
            
            # Build dynamic WIQL query
            query_conditions = [f"[System.TeamProject] = '{project_name}'"]
            
            if work_item_type != "all":
                query_conditions.append(f"[System.WorkItemType] = '{work_item_type}'")
            
            if area_path:
                query_conditions.append(f"[System.AreaPath] UNDER '{area_path}'")
            
            if state:
                query_conditions.append(f"[System.State] = '{state}'")
            
            if from_date:
                query_conditions.append(f"[System.CreatedDate] >= '{from_date}'")
            
            if to_date:
                query_conditions.append(f"[System.CreatedDate] <= '{to_date}'")

            # Build complete WIQL query
            wiql_query = f"SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], [System.AssignedTo], [System.CreatedDate], [System.ChangedDate], [Microsoft.VSTS.Common.Priority], [Microsoft.VSTS.Common.Severity], [System.AreaPath], [System.Tags], [System.Description] FROM WorkItems WHERE {' AND '.join(query_conditions)} ORDER BY [System.CreatedDate] DESC"

            # Execute WIQL query
            wiql_url = f"{ADO_ORG_URL}/{project_encoded}/_apis/wit/wiql?api-version=7.1"
            wiql_payload = {"query": wiql_query}

            response = self.session.post(wiql_url, json=wiql_payload)
            response.raise_for_status()

            wiql_result = response.json()
            work_item_ids = [item["id"] for item in wiql_result.get("workItems", [])]

            if not work_item_ids:
                return json.dumps({
                    "bugs": [],
                    "total_count": 0,
                    "filters_applied": {
                        "project": project_name,
                        "area_path": area_path,
                        "from_date": from_date,
                        "to_date": to_date,
                        "work_item_type": work_item_type,
                        "state": state
                    },
                    "message": "No bugs found with the specified filters"
                }, indent=2)

            # Limit results
            work_item_ids = work_item_ids[:limit]

            # Get detailed work item information
            work_items_url = f"{ADO_ORG_URL}/{project_encoded}/_apis/wit/workitems?ids={','.join(map(str, work_item_ids))}&$expand=fields&api-version=7.1"

            details_response = self.session.get(work_items_url)
            details_response.raise_for_status()

            work_items_data = details_response.json()

            # Format bug data for analysis
            bugs = []
            for item in work_items_data.get("value", []):
                fields = item.get("fields", {})

                bug = {
                    "id": item.get("id"),
                    "title": fields.get("System.Title", ""),
                    "description": fields.get("System.Description", ""),
                    "type": fields.get("System.WorkItemType", "Bug"),
                    "state": fields.get("System.State", ""),
                    "assigned_to": fields.get("System.AssignedTo", {}).get("displayName", "Unassigned") if fields.get("System.AssignedTo") else "Unassigned",
                    "created_date": fields.get("System.CreatedDate", ""),
                    "changed_date": fields.get("System.ChangedDate", ""),
                    "priority": fields.get("Microsoft.VSTS.Common.Priority", ""),
                    "severity": fields.get("Microsoft.VSTS.Common.Severity", ""),
                    "area_path": fields.get("System.AreaPath", ""),
                    "tags": fields.get("System.Tags", "").split(";") if fields.get("System.Tags") else [],
                    "url": f"{ADO_ORG_URL}/{project_encoded}/_workitems/edit/{item.get('id')}"
                }
                bugs.append(bug)

            logger.info(f"Successfully fetched {len(bugs)} bugs from {project_name}")

            return json.dumps({
                "bugs": bugs,
                "total_count": len(bugs),
                "filters_applied": {
                    "project": project_name,
                    "area_path": area_path,
                    "from_date": from_date,
                    "to_date": to_date,
                    "work_item_type": work_item_type,
                    "state": state
                },
                "organization": ADO_ORG_URL
            }, indent=2)

        except Exception as e:
            logger.error(f"Failed to fetch bugs: {str(e)}")
            return json.dumps({"error": f"Failed to fetch bugs: {str(e)}"})
    
    async def _get_projects(self) -> str:
        """Get list of all available projects"""
        try:
            if not ADO_PAT or not ADO_ORG_URL:
                return json.dumps({"error": "ADO credentials not configured"})

            projects_url = f"{ADO_ORG_URL}/_apis/projects?api-version=7.1"
            response = self.session.get(projects_url)
            response.raise_for_status()

            projects_data = response.json()
            projects = []

            for project in projects_data.get("value", []):
                projects.append({
                    "id": project.get("id"),
                    "name": project.get("name"),
                    "description": project.get("description", ""),
                    "state": project.get("state", "")
                })

            logger.info(f"Found {len(projects)} available projects")
            
            return json.dumps({
                "projects": projects,
                "total_count": len(projects),
                "organization": ADO_ORG_URL
            }, indent=2)

        except Exception as e:
            logger.error(f"Failed to fetch projects: {str(e)}")
            return json.dumps({"error": f"Failed to fetch projects: {str(e)}"})
    
    async def _get_area_paths(self, project_name: str) -> str:
        """Get area paths for a specific project"""
        try:
            if not ADO_PAT or not ADO_ORG_URL:
                return json.dumps({"error": "ADO credentials not configured"})

            project_encoded = quote(project_name)
            areas_url = f"{ADO_ORG_URL}/{project_encoded}/_apis/wit/classtificationnodes/Areas?$depth=10&api-version=7.1"
            
            response = self.session.get(areas_url)
            response.raise_for_status()

            areas_data = response.json()
            area_paths = []

            def extract_paths(node, parent_path=""):
                current_path = f"{parent_path}\\{node['name']}" if parent_path else node['name']
                area_paths.append({
                    "name": node['name'],
                    "path": current_path,
                    "id": node.get('id')
                })
                
                for child in node.get('children', []):
                    extract_paths(child, current_path)

            if areas_data:
                extract_paths(areas_data)

            logger.info(f"Found {len(area_paths)} area paths for project {project_name}")

            return json.dumps({
                "area_paths": area_paths,
                "project": project_name,
                "total_count": len(area_paths)
            }, indent=2)

        except Exception as e:
            logger.error(f"Failed to fetch area paths: {str(e)}")
            return json.dumps({"error": f"Failed to fetch area paths: {str(e)}"})
    
    async def _analyze_bug_patterns(self, project_name: str, area_path: str = "", days_back: int = 90) -> str:
        """Analyze bugs for patterns and root causes"""
        try:
            # Calculate date range for analysis
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Fetch bugs for pattern analysis
            bugs_json = await self._fetch_bugs(
                project_name=project_name,
                area_path=area_path,
                from_date=start_date.strftime("%Y-%m-%d"),
                to_date=end_date.strftime("%Y-%m-%d"),
                limit=500
            )
            
            bugs_data = json.loads(bugs_json)
            if "error" in bugs_data:
                return bugs_json
                
            bugs = bugs_data.get("bugs", [])
            
            # Analyze patterns
            patterns = {
                "total_bugs": len(bugs),
                "state_distribution": {},
                "priority_distribution": {},
                "severity_distribution": {},
                "area_distribution": {},
                "assignee_distribution": {},
                "timeline_patterns": {},
                "common_keywords": {},
                "potential_root_causes": []
            }
            
            # Analyze state distribution
            for bug in bugs:
                state = bug.get("state", "Unknown")
                patterns["state_distribution"][state] = patterns["state_distribution"].get(state, 0) + 1
                
                priority = bug.get("priority", "Unknown")
                patterns["priority_distribution"][priority] = patterns["priority_distribution"].get(priority, 0) + 1
                
                severity = bug.get("severity", "Unknown")
                patterns["severity_distribution"][severity] = patterns["severity_distribution"].get(severity, 0) + 1
                
                area = bug.get("area_path", "Unknown")
                patterns["area_distribution"][area] = patterns["area_distribution"].get(area, 0) + 1
                
                assignee = bug.get("assigned_to", "Unassigned")
                patterns["assignee_distribution"][assignee] = patterns["assignee_distribution"].get(assignee, 0) + 1
            
            # Identify potential root causes based on patterns
            if len(bugs) > 0:
                # High severity bugs indicate potential system issues
                high_severity_count = patterns["severity_distribution"].get("1 - Critical", 0) + patterns["severity_distribution"].get("2 - High", 0)
                if high_severity_count > len(bugs) * 0.3:
                    patterns["potential_root_causes"].append({
                        "category": "System Stability",
                        "description": "High number of critical/high severity bugs suggests system stability issues",
                        "recommendation": "Focus on infrastructure and core system components"
                    })
                
                # Many bugs in same area suggest module-specific issues
                if patterns["area_distribution"]:
                    max_area = max(patterns["area_distribution"], key=patterns["area_distribution"].get)
                    max_area_count = patterns["area_distribution"][max_area]
                    if max_area_count > len(bugs) * 0.4:
                        patterns["potential_root_causes"].append({
                            "category": "Module-Specific Issue",
                            "description": f"High concentration of bugs in {max_area}",
                            "recommendation": f"Deep dive into {max_area} module for structural issues"
                        })

            logger.info(f"Analyzed {len(bugs)} bugs for patterns")
            
            return json.dumps({
                "analysis_summary": patterns,
                "period_analyzed": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                "project": project_name,
                "area_path": area_path
            }, indent=2)

        except Exception as e:
            logger.error(f"Failed to analyze bug patterns: {str(e)}")
            return json.dumps({"error": f"Failed to analyze bug patterns: {str(e)}"})
    
    async def _get_bug_details(self, project_name: str, bug_id: int) -> str:
        """Get detailed information about a specific bug"""
        try:
            if not ADO_PAT or not ADO_ORG_URL:
                return json.dumps({"error": "ADO credentials not configured"})

            project_encoded = quote(project_name)
            work_item_url = f"{ADO_ORG_URL}/{project_encoded}/_apis/wit/workitems/{bug_id}?$expand=all&api-version=7.1"

            response = self.session.get(work_item_url)

            if response.status_code == 404:
                return json.dumps({"error": f"Bug {bug_id} not found in project {project_name}"})

            response.raise_for_status()
            work_item_data = response.json()
            fields = work_item_data.get("fields", {})

            # Get comments
            comments = []
            try:
                comments_url = f"{ADO_ORG_URL}/{project_encoded}/_apis/wit/workitems/{bug_id}/comments?api-version=7.1"
                comments_response = self.session.get(comments_url)
                if comments_response.status_code == 200:
                    comments_data = comments_response.json()
                    for comment in comments_data.get("comments", []):
                        comments.append({
                            "author": comment.get("createdBy", {}).get("displayName", "Unknown"),
                            "date": comment.get("createdDate", ""),
                            "text": comment.get("text", "")
                        })
            except:
                pass

            bug_details = {
                "id": work_item_data.get("id"),
                "title": fields.get("System.Title", ""),
                "description": fields.get("System.Description", ""),
                "reproduction_steps": fields.get("Microsoft.VSTS.TCM.ReproSteps", ""),
                "type": fields.get("System.WorkItemType", "Bug"),
                "state": fields.get("System.State", ""),
                "assigned_to": fields.get("System.AssignedTo", {}).get("displayName", "Unassigned") if fields.get("System.AssignedTo") else "Unassigned",
                "created_date": fields.get("System.CreatedDate", ""),
                "changed_date": fields.get("System.ChangedDate", ""),
                "resolved_date": fields.get("Microsoft.VSTS.Common.ResolvedDate", ""),
                "priority": fields.get("Microsoft.VSTS.Common.Priority", ""),
                "severity": fields.get("Microsoft.VSTS.Common.Severity", ""),
                "area_path": fields.get("System.AreaPath", ""),
                "iteration_path": fields.get("System.IterationPath", ""),
                "tags": fields.get("System.Tags", "").split(";") if fields.get("System.Tags") else [],
                "comments": comments,
                "url": f"{ADO_ORG_URL}/{project_encoded}/_workitems/edit/{bug_id}"
            }

            return json.dumps(bug_details, indent=2)

        except Exception as e:
            logger.error(f"Failed to get bug details: {str(e)}")
            return json.dumps({"error": f"Failed to get bug details: {str(e)}"})

    async def _get_recent_bugs(self, days: int = 7) -> str:
        """Get recent bugs across all projects"""
        try:
            # This would need to be implemented based on specific requirements
            # For now, return a placeholder
            return json.dumps({
                "message": "Recent bugs endpoint - implementation depends on specific project selection",
                "suggestion": "Use fetch_bugs with specific project and date range"
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to get recent bugs: {str(e)}"})


async def main():
    """Main server entry point"""
    server_instance = AdoBugAnalyzerMCPServer()

    # Run the server using stdin/stdout
    import sys
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="ado-bug-analyzer",
                server_version="1.0.0",
                capabilities=server_instance.server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
