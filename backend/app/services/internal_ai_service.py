"""
Thomson Reuters OpenArena AI Service
===================================

This service provides integration with Thomson Reuters' OpenArena AI platform
using ESSO token authentication and the inference API.
"""

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any
import aiohttp
from datetime import datetime

from ..core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class InternalAIService:
    """
    Thomson Reuters OpenArena AI service for bug analysis using enterprise AI infrastructure
    Uses ESSO token authentication and OpenArena inference API
    """
    
    def __init__(self):
        self.esso_token = settings.esso_token
        self.base_url = settings.open_arena_base_url
        self.workflow_id = settings.open_arena_workflow_id
        self.timeout = settings.ai_service_timeout
        self.max_retries = settings.ai_max_retries
        
        # Session management
        self.session = None
        
        logger.info("Thomson Reuters OpenArena AI Service initialized")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with proper headers"""
        if self.session is None or self.session.closed:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.esso_token}",
                "User-Agent": "AI-Bug-Analyzer/1.0"
            }
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout
            )
        
        return self.session
    
    async def _make_inference_request(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Make inference request to OpenArena API with retry logic"""
        payload = {
            "workflow_id": self.workflow_id,
            "query": query,
            "is_persistence_allowed": False
        }
        
        # Add context if provided
        if context:
            payload["context"] = context
        
        url = f"{self.base_url}/v1/inference"
        
        for attempt in range(self.max_retries + 1):
            try:
                session = await self._get_session()
                
                async with session.post(url, json=payload) as response:
                    return await self._handle_response(response)
                
            except aiohttp.ClientError as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                logger.error(f"Unexpected error in AI request: {str(e)}")
                raise
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle OpenArena API response and error codes"""
        if response.status == 401:
            logger.error("Authentication failed - check ESSO token")
            raise ValueError("Invalid ESSO token or authentication failed")
        
        if response.status == 429:
            logger.warning("Rate limit exceeded - implementing backoff")
            await asyncio.sleep(5)
            raise aiohttp.ClientError("Rate limit exceeded")
        
        if response.status >= 400:
            error_text = await response.text()
            logger.error(f"OpenArena API error {response.status}: {error_text}")
            raise ValueError(f"OpenArena API error: {response.status} - {error_text}")
        
        try:
            return await response.json()
        except json.JSONDecodeError:
            text = await response.text()
            logger.error(f"Invalid JSON response: {text}")
            raise ValueError("Invalid JSON response from OpenArena API")
    
    async def find_duplicate_bugs(self, 
                                 query_text: str, 
                                 existing_bugs: List[Dict[str, Any]],
                                 threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Find duplicate bugs using Thomson Reuters OpenArena AI
        """
        if threshold is None:
            threshold = settings.ai_similarity_threshold
        
        logger.info(f"Finding duplicates using OpenArena AI for query with {len(existing_bugs)} existing bugs")
        
        # Format prompt for duplicate detection
        context_bugs = []
        for i, bug in enumerate(existing_bugs[:10]):  # Limit to prevent payload size issues
            bug_summary = {
                "id": bug.get("id", f"bug_{i}"),
                "title": bug.get("title", ""),
                "description": bug.get("description", "")[:200] + "..." if len(bug.get("description", "")) > 200 else bug.get("description", "")
            }
            context_bugs.append(bug_summary)
        
        context = f"Existing bugs to compare against:\n{json.dumps(context_bugs, indent=2)}"
        
        query = f"""Find duplicate bugs for the following query:
"{query_text}"

Please analyze the query against the existing bugs and identify potential duplicates.
Return a JSON response with an array of potential duplicates, each containing:
- bug_id: The ID of the potentially duplicate bug
- title: The title of the bug
- similarity_score: A score from 0-100 indicating how similar it is
- explanation: Why this might be a duplicate
- highlights: Key matching phrases

Only include bugs with similarity score >= {threshold * 100}. Format as valid JSON."""
        
        try:
            # Call OpenArena inference API
            response = await self._make_inference_request(query, context)
            
            # Extract answer from OpenArena response
            result = response.get("result", {})
            answer = result.get("answer", "")
            
            # Try to parse JSON from the answer
            try:
                # Look for JSON in the answer
                import re
                json_match = re.search(r'\[.*\]', answer, re.DOTALL)
                if json_match:
                    duplicates_data = json.loads(json_match.group())
                else:
                    logger.warning("No JSON array found in OpenArena response")
                    duplicates_data = []
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from OpenArena response")
                duplicates_data = []
            
            # Format duplicates for our API
            duplicates = []
            for dup in duplicates_data:
                if isinstance(dup, dict):
                    # Find the original bug data
                    original_bug = next((b for b in existing_bugs if str(b.get("id")) == str(dup.get("bug_id"))), {})
                    
                    duplicate = {
                        "bug_id": dup.get("bug_id"),
                        "ado_id": original_bug.get("ado_id"),
                        "title": dup.get("title", original_bug.get("title", "")),
                        "description": original_bug.get("description", "")[:200] + "..." if len(original_bug.get("description", "")) > 200 else original_bug.get("description", ""),
                        "similarity_score": dup.get("similarity_score", 0),
                        "explanation": dup.get("explanation", ""),
                        "highlights": dup.get("highlights", []),
                        "confidence": dup.get("similarity_score", 0),
                        "created_date": original_bug.get("created_date"),
                        "state": original_bug.get("state"),
                        "priority": original_bug.get("priority"),
                        "url": original_bug.get("url")
                    }
                    duplicates.append(duplicate)
            
            logger.info(f"OpenArena AI found {len(duplicates)} potential duplicates")
            return duplicates
            
        except Exception as e:
            logger.error(f"Error in OpenArena duplicate detection: {str(e)}")
            raise
    
    async def analyze_root_causes(self, bugs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze bugs for root cause patterns using OpenArena AI
        """
        logger.info(f"Analyzing root causes using OpenArena AI for {len(bugs)} bugs")
        
        # Format bugs data for analysis
        bugs_summary = []
        for bug in bugs[:20]:  # Limit to prevent payload size issues
            bug_data = {
                "id": bug.get("id"),
                "title": bug.get("title", ""),
                "description": bug.get("description", "")[:150] + "..." if len(bug.get("description", "")) > 150 else bug.get("description", ""),
                "state": bug.get("state"),
                "priority": bug.get("priority"),
                "area_path": bug.get("area_path")
            }
            bugs_summary.append(bug_data)
        
        context = f"Bug data for analysis:\n{json.dumps(bugs_summary, indent=2)}"
        
        query = f"""Analyze the following {len(bugs)} bugs for root cause patterns and categorize them.

Please provide a comprehensive root cause analysis in JSON format with:
- total_bugs_analyzed: number of bugs analyzed
- categories: categorized bugs by root cause (e.g., "System Stability", "API Issues", "UI/UX Problems", "Configuration Issues", "Data/Database Issues", "Authentication/Security", "Performance Issues", "Environment Issues")
- recommendations: actionable recommendations for each category
- patterns: summary of patterns found

Format the response as valid JSON."""
        
        try:
            response = await self._make_inference_request(query, context)
            
            # Extract answer from OpenArena response
            result = response.get("result", {})
            answer = result.get("answer", "")
            
            # Try to parse JSON from the answer
            try:
                import re
                json_match = re.search(r'\{.*\}', answer, re.DOTALL)
                if json_match:
                    analysis_result = json.loads(json_match.group())
                else:
                    logger.warning("No JSON found in OpenArena root cause response")
                    analysis_result = {}
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from OpenArena root cause response")
                analysis_result = {}
            
            # Ensure required structure
            root_cause_analysis = {
                "total_bugs_analyzed": len(bugs),
                "categories": analysis_result.get("categories", {}),
                "recommendations": analysis_result.get("recommendations", []),
                "patterns": analysis_result.get("patterns", {}),
                "ai_confidence": 85,  # Default confidence
                "processing_time": 0
            }
            
            logger.info(f"OpenArena AI root cause analysis completed")
            return root_cause_analysis
            
        except Exception as e:
            logger.error(f"Error in OpenArena root cause analysis: {str(e)}")
            raise
    
    async def generate_bug_insights(self, bug: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI insights for a specific bug using OpenArena AI"""
        logger.info(f"Generating bug insights using OpenArena AI for bug {bug.get('id', 'unknown')}")
        
        bug_data = {
            "id": bug.get("id"),
            "title": bug.get("title", ""),
            "description": bug.get("description", ""),
            "state": bug.get("state"),
            "priority": bug.get("priority"),
            "area_path": bug.get("area_path"),
            "tags": bug.get("tags", [])
        }
        
        context = f"Bug details:\n{json.dumps(bug_data, indent=2)}"
        
        query = f"""Generate comprehensive insights for this bug.

Please provide insights in JSON format with:
- summary: Brief summary of the bug
- likely_cause: Most probable cause of the issue
- testing_focus: Array of testing recommendations
- related_areas: Array of system areas that might be affected
- keywords: Array of key technical terms

Format the response as valid JSON."""
        
        try:
            response = await self._make_inference_request(query, context)
            
            # Extract answer from OpenArena response
            result = response.get("result", {})
            answer = result.get("answer", "")
            
            # Try to parse JSON from the answer
            try:
                import re
                json_match = re.search(r'\{.*\}', answer, re.DOTALL)
                if json_match:
                    insights_data = json.loads(json_match.group())
                else:
                    logger.warning("No JSON found in OpenArena insights response")
                    insights_data = {}
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from OpenArena insights response")
                insights_data = {}
            
            insights = {
                "summary": insights_data.get("summary", ""),
                "likely_cause": insights_data.get("likely_cause", ""),
                "testing_focus": insights_data.get("testing_focus", []),
                "related_areas": insights_data.get("related_areas", []),
                "keywords": insights_data.get("keywords", []),
                "confidence": 85,
                "ai_model_version": "OpenArena"
            }
            
            logger.info(f"Bug insights generated with OpenArena AI")
            return insights
            
        except Exception as e:
            logger.error(f"Error generating bug insights with OpenArena AI: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health and connectivity of OpenArena AI service"""
        try:
            # Simple test query
            test_response = await self._make_inference_request("Hello, this is a health check test")
            
            return {
                "status": "healthy",
                "ai_service": "OpenArena",
                "workflow_available": bool(test_response.get("result")),
                "response_time": 0,
                "model_version": "OpenArena API"
            }
            
        except Exception as e:
            logger.error(f"OpenArena AI health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "ai_service": "OpenArena unavailable"
            }
    
    async def validate_configuration(self) -> Dict[str, Any]:
        """Validate OpenArena AI configuration and credentials"""
        validation_result = {
            "esso_token_configured": bool(self.esso_token),
            "base_url_configured": bool(self.base_url),
            "workflow_id_configured": bool(self.workflow_id),
            "configuration_valid": False,
            "errors": []
        }
        
        # Check required configuration
        if not self.esso_token:
            validation_result["errors"].append("ESSO token not configured")
        
        if not self.base_url:
            validation_result["errors"].append("OpenArena base URL not configured")
        
        if not self.workflow_id:
            validation_result["errors"].append("OpenArena workflow ID not configured")
        
        # Test connectivity if configuration looks good
        if not validation_result["errors"]:
            try:
                health_status = await self.health_check()
                if health_status.get("status") == "healthy":
                    validation_result["configuration_valid"] = True
                    validation_result["auth_test"] = "successful"
                else:
                    validation_result["errors"].append(f"Service health check failed: {health_status.get('error', 'Unknown error')}")
            except Exception as e:
                validation_result["errors"].append(f"Connectivity test failed: {str(e)}")
        
        return validation_result
    
    async def analyze_general_query(self, query: str) -> str:
        """
        Analyze a general query using OpenArena AI - for help assistant functionality
        """
        logger.info(f"Processing general query using OpenArena AI")
        
        try:
            response = await self._make_inference_request(query)
            
            # Extract answer from OpenArena response
            result = response.get("result", {})
            answer = result.get("answer", "")
            
            if not answer:
                logger.warning("Empty response from OpenArena AI")
                return "I'm sorry, but I couldn't generate a response at this time. Please try again later."
            
            logger.info(f"General query processed successfully with OpenArena AI")
            return answer
            
        except Exception as e:
            logger.error(f"Error processing general query with OpenArena AI: {str(e)}")
            raise

    async def close(self):
        """Clean up resources"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("OpenArena AI service session closed")


# Global service instance
internal_ai_service = InternalAIService()

def get_internal_ai_service() -> InternalAIService:
    """Get internal AI service instance"""
    return internal_ai_service
