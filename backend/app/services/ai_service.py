"""
AI Service for Duplicate Detection and Analysis
==============================================

This service provides AI-powered analysis capabilities including:
- Semantic similarity for duplicate detection
- Root cause analysis
- Bug pattern analysis
- Text processing and embedding generation
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
import asyncio
import re
from datetime import datetime

# AI and ML imports
try:
    from sentence_transformers import SentenceTransformer, util
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_ML_LIBS = True
except ImportError:
    HAS_ML_LIBS = False
    logging.warning("ML libraries not available. Install sentence-transformers and scikit-learn for full functionality.")

from ..core.config import get_settings
from .internal_ai_service import get_internal_ai_service

settings = get_settings()
logger = logging.getLogger(__name__)

class AIService:
    """
    AI service for bug analysis, duplicate detection, and insights
    Supports both local AI models and external AI integration
    """
    
    def __init__(self):
        self.model = None
        self.tfidf_vectorizer = None
        self.similarity_threshold = settings.ai_similarity_threshold
        
        if HAS_ML_LIBS:
            try:
                self.model = SentenceTransformer(settings.ai_model_name)
                self.tfidf_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
                logger.info(f"AI model {settings.ai_model_name} loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load AI model: {str(e)}")
                self.model = None
        
        logger.info("AI Service initialized")
    
    def clean_text(self, text: str) -> str:
        """Clean and preprocess text for analysis"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep alphanumeric and basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?]', ' ', text)
        
        return text.strip()
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract key terms from text using TF-IDF"""
        if not text or not HAS_ML_LIBS:
            return []
        
        try:
            cleaned_text = self.clean_text(text)
            if len(cleaned_text) < 10:
                return []
            
            # Use TF-IDF to extract keywords
            tfidf_matrix = self.tfidf_vectorizer.fit_transform([cleaned_text])
            feature_names = self.tfidf_vectorizer.get_feature_names_out()
            scores = tfidf_matrix.toarray()[0]
            
            # Get top keywords
            keyword_scores = list(zip(feature_names, scores))
            keyword_scores.sort(key=lambda x: x[1], reverse=True)
            
            keywords = [kw for kw, score in keyword_scores[:max_keywords] if score > 0.1]
            return keywords
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {str(e)}")
            return []
    
    async def find_duplicate_bugs(self, 
                                 query_text: str, 
                                 existing_bugs: List[Dict[str, Any]],
                                 threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Find duplicate bugs using semantic similarity
        Returns list of similar bugs with similarity scores and explanations
        """
        if threshold is None:
            threshold = self.similarity_threshold
        
        logger.info(f"Finding duplicates for query with {len(existing_bugs)} existing bugs")
        
        # Use internal AI if configured
        if settings.use_internal_ai:
            try:
                internal_ai = get_internal_ai_service()
                logger.info("Using Thomson Reuters internal AI for duplicate detection")
                return await internal_ai.find_duplicate_bugs(query_text, existing_bugs, threshold)
            except Exception as e:
                logger.warning(f"Internal AI failed, falling back to local models: {str(e)}")
        
        if not self.model or not HAS_ML_LIBS:
            # Fallback to keyword-based matching
            return await self._keyword_based_duplicate_detection(query_text, existing_bugs, threshold)
        
        try:
            # Clean and prepare query text
            query_cleaned = self.clean_text(query_text)
            if not query_cleaned:
                return []
            
            # Generate embedding for query
            query_embedding = self.model.encode(query_cleaned)
            
            duplicates = []
            
            for bug in existing_bugs:
                # Combine title and description for comparison
                bug_text = f"{bug.get('title', '')} {bug.get('description', '')}"
                bug_cleaned = self.clean_text(bug_text)
                
                if not bug_cleaned:
                    continue
                
                # Generate embedding for bug
                bug_embedding = self.model.encode(bug_cleaned)
                
                # Calculate similarity
                similarity = util.cos_sim(query_embedding, bug_embedding).item()
                
                if similarity >= threshold:
                    # Generate explanation
                    explanation = await self._generate_similarity_explanation(
                        query_cleaned, bug_cleaned, similarity
                    )
                    
                    # Highlight matching phrases
                    highlights = self._find_matching_phrases(query_cleaned, bug_cleaned)
                    
                    duplicate = {
                        "bug_id": bug.get("id"),
                        "ado_id": bug.get("ado_id"),
                        "title": bug.get("title"),
                        "description": bug.get("description", "")[:200] + "..." if len(bug.get("description", "")) > 200 else bug.get("description", ""),
                        "similarity_score": round(similarity * 100, 2),
                        "explanation": explanation,
                        "highlights": highlights,
                        "created_date": bug.get("created_date"),
                        "state": bug.get("state"),
                        "priority": bug.get("priority"),
                        "url": bug.get("url")
                    }
                    
                    duplicates.append(duplicate)
            
            # Sort by similarity score (highest first)
            duplicates.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            # Limit results
            duplicates = duplicates[:settings.max_similarity_results]
            
            logger.info(f"Found {len(duplicates)} potential duplicates")
            return duplicates
            
        except Exception as e:
            logger.error(f"Error in duplicate detection: {str(e)}")
            # Fallback to keyword-based matching
            return await self._keyword_based_duplicate_detection(query_text, existing_bugs, threshold)
    
    async def _keyword_based_duplicate_detection(self, 
                                               query_text: str, 
                                               existing_bugs: List[Dict[str, Any]],
                                               threshold: float) -> List[Dict[str, Any]]:
        """Simple bucket-based duplicate detection with clear similarity ranges"""
        logger.info("Using bucket-based duplicate detection")
        
        query_cleaned = self.clean_text(query_text).lower()
        query_words = query_cleaned.split()
        duplicates = []
        
        for bug in existing_bugs:
            bug_text = f"{bug.get('title', '')} {bug.get('description', '')}"
            bug_cleaned = self.clean_text(bug_text).lower()
            bug_words = bug_cleaned.split()
            
            # Calculate similarity and assign to buckets
            similarity_score, category, explanation = self._calculate_similarity_bucket(
                query_words, bug_words, query_cleaned, bug_cleaned
            )
            
            # Convert threshold percentage to decimal for comparison
            threshold_decimal = threshold
            
            # Only include if similarity meets threshold
            if similarity_score >= threshold_decimal:
                # Find common terms for highlighting
                query_set = set(query_words)
                bug_set = set(bug_words)
                common_terms = list(query_set.intersection(bug_set))
                
                duplicate = {
                    "bug_id": bug.get("id"),
                    "ado_id": bug.get("ado_id"),
                    "title": bug.get("title"),
                    "description": bug.get("description", "")[:200] + "..." if len(bug.get("description", "")) > 200 else bug.get("description", ""),
                    "similarity_score": round(similarity_score * 100, 1),
                    "explanation": f"{category}: {explanation}",
                    "highlights": common_terms[:8],
                    "created_date": bug.get("created_date"),
                    "state": bug.get("state"),
                    "priority": bug.get("priority"),
                    "url": bug.get("url")
                }
                
                duplicates.append(duplicate)
        
        # Sort by similarity score (highest first)
        duplicates.sort(key=lambda x: x["similarity_score"], reverse=True)
        return duplicates[:settings.max_similarity_results]
    
    def _calculate_similarity_bucket(self, query_words, bug_words, query_text, bug_text):
        """Calculate similarity and assign to appropriate bucket (0-25, 26-50, 51-75, 76-100)"""
        
        # Count exact word matches
        query_set = set(query_words)
        bug_set = set(bug_words)
        exact_matches = len(query_set.intersection(bug_set))
        
        # Check for substring matches (partial word matching)
        substring_matches = 0
        for q_word in query_words:
            if len(q_word) >= 3 and q_word in bug_text:
                substring_matches += 1
        
        # Calculate different similarity metrics
        if len(query_words) == 0:
            return 0.0, "No Content", "Empty query"
        
        exact_ratio = exact_matches / len(query_words)
        substring_ratio = substring_matches / len(query_words)
        
        # Special case: Check for nearly identical content
        if exact_ratio >= 0.9:
            return 0.95, "Nearly Identical", f"{exact_matches}/{len(query_words)} exact words match"
        elif exact_ratio >= 0.7:
            return 0.85, "Very Similar", f"{exact_matches}/{len(query_words)} exact words match"
        elif exact_ratio >= 0.5:
            return 0.65, "Quite Similar", f"{exact_matches}/{len(query_words)} exact words match"
        elif substring_ratio >= 0.7:
            return 0.60, "Good Substring Match", f"{substring_matches}/{len(query_words)} words found as substrings"
        elif exact_ratio >= 0.3:
            return 0.45, "Moderate Match", f"{exact_matches}/{len(query_words)} exact words match"
        elif substring_ratio >= 0.4:
            return 0.40, "Some Substring Match", f"{substring_matches}/{len(query_words)} words found as substrings"
        elif exact_ratio >= 0.1:
            return 0.25, "Low Match", f"{exact_matches}/{len(query_words)} exact words match"
        else:
            return 0.10, "Very Low Match", f"Only {exact_matches}/{len(query_words)} words match"
    
    async def _generate_similarity_explanation(self, query: str, bug_text: str, similarity: float) -> str:
        """Generate explanation for why bugs are similar"""
        if similarity >= 0.95:
            return "Nearly identical content - likely exact duplicate"
        elif similarity >= 0.90:
            return "Very high similarity in title and description"
        elif similarity >= 0.85:
            return "High similarity with overlapping key concepts"
        else:
            return "Moderate similarity with some common elements"
    
    def _find_matching_phrases(self, query: str, bug_text: str) -> List[str]:
        """Find matching phrases between query and bug text"""
        query_words = set(query.lower().split())
        bug_words = set(bug_text.lower().split())
        matches = list(query_words.intersection(bug_words))
        return matches[:10]  # Limit to top 10 matches
    
    async def analyze_root_causes(self, bugs: List[Dict[str, Any]], analysis_depth: str = "standard") -> Dict[str, Any]:
        """
        Analyze bugs for root cause patterns with different depth levels
        
        Args:
            bugs: List of bugs to analyze
            analysis_depth: "standard", "detailed", or "comprehensive"
            
        Returns categorized analysis with recommendations
        """
        logger.info(f"Analyzing root causes for {len(bugs)} bugs with {analysis_depth} depth")
        
        # Use internal AI if configured
        if settings.use_internal_ai:
            try:
                internal_ai = get_internal_ai_service()
                logger.info("Using Thomson Reuters internal AI for root cause analysis")
                return await internal_ai.analyze_root_causes(bugs)
            except Exception as e:
                logger.warning(f"Internal AI failed, falling back to local analysis: {str(e)}")
        
        root_cause_analysis = {
            "total_bugs_analyzed": len(bugs),
            "categories": {
                "System Stability": [],
                "API Issues": [],
                "UI/UX Problems": [],
                "Configuration Issues": [],
                "Data/Database Issues": [],
                "Authentication/Security": [],
                "Performance Issues": [],
                "Environment Issues": []
            },
            "recommendations": [],
            "patterns": {}
        }
        
        # Keywords for each category
        category_keywords = {
            "System Stability": ["crash", "freeze", "hang", "memory", "exception", "error", "fail"],
            "API Issues": ["api", "endpoint", "request", "response", "timeout", "connection", "service"],
            "UI/UX Problems": ["button", "page", "display", "layout", "ui", "interface", "render"],
            "Configuration Issues": ["config", "setting", "parameter", "environment", "deployment"],
            "Data/Database Issues": ["database", "data", "query", "table", "connection", "sql"],
            "Authentication/Security": ["login", "auth", "permission", "access", "security", "token"],
            "Performance Issues": ["slow", "performance", "speed", "latency", "timeout", "load"],
            "Environment Issues": ["browser", "device", "platform", "version", "compatibility"]
        }
        
        # Analyze each bug with improved text processing
        for bug in bugs:
            # Clean and combine bug text from multiple fields
            title = self.clean_text(bug.get('title', '')).lower()
            description = self.clean_text(bug.get('description', '')).lower()
            reason = self.clean_text(bug.get('reason', '')).lower()
            area_path = str(bug.get('area_path', '')).lower()
            tags = ' '.join(bug.get('tags', [])).lower() if isinstance(bug.get('tags'), list) else str(bug.get('tags', '')).lower()
            
            # Combine all text fields for analysis
            bug_text = f"{title} {description} {reason} {area_path} {tags}"
            bug_categories = []
            
            # Check against each category with enhanced matching
            for category, keywords in category_keywords.items():
                score = 0
                # Direct keyword matches
                score += sum(1 for keyword in keywords if keyword in bug_text)
                
                # Bonus for title matches (more important)
                score += sum(0.5 for keyword in keywords if keyword in title)
                
                # Bonus for area path matches
                score += sum(0.3 for keyword in keywords if keyword in area_path)
                
                if score > 0:
                    bug_categories.append((category, score))
            
            # Assign to best matching category, or create a general category if no match
            if bug_categories:
                bug_categories.sort(key=lambda x: x[1], reverse=True)
                best_category = bug_categories[0][0]
                
                root_cause_analysis["categories"][best_category].append({
                    "bug_id": bug.get("id"),
                    "ado_id": bug.get("ado_id"),
                    "title": bug.get("title"),
                    "confidence": round(bug_categories[0][1], 1),
                    "matched_keywords": [kw for kw in category_keywords[best_category] if kw in bug_text][:3]
                })
            else:
                # Add to general category for uncategorized bugs
                if "General Issues" not in root_cause_analysis["categories"]:
                    root_cause_analysis["categories"]["General Issues"] = []
                
                root_cause_analysis["categories"]["General Issues"].append({
                    "bug_id": bug.get("id"),
                    "ado_id": bug.get("ado_id"),
                    "title": bug.get("title"),
                    "confidence": 0.5,
                    "matched_keywords": []
                })
        
        # Apply analysis depth-specific enhancements
        root_cause_analysis = await self._apply_analysis_depth(root_cause_analysis, bugs, analysis_depth)
        
        # Generate recommendations based on patterns (adjusted for small datasets)
        min_threshold = max(1, len(bugs) * 0.15)  # Lower threshold for small datasets, minimum 1 bug
        for category, bugs_in_category in root_cause_analysis["categories"].items():
            if len(bugs_in_category) >= min_threshold:
                recommendation = self._generate_root_cause_recommendation(category, len(bugs_in_category), analysis_depth)
                root_cause_analysis["recommendations"].append(recommendation)
        
        # Calculate patterns
        root_cause_analysis["patterns"] = {
            category: len(bugs_list) for category, bugs_list in root_cause_analysis["categories"].items()
        }
        
        logger.info(f"Root cause analysis completed: {len(root_cause_analysis['recommendations'])} recommendations generated")
        return root_cause_analysis
    
    async def _apply_analysis_depth(self, analysis: Dict[str, Any], bugs: List[Dict[str, Any]], depth: str) -> Dict[str, Any]:
        """Apply depth-specific enhancements to the analysis"""
        
        if depth == "detailed":
            # Add detailed analysis features
            analysis["severity_breakdown"] = self._analyze_severity_patterns(bugs)
            analysis["temporal_patterns"] = self._analyze_temporal_patterns(bugs)
            analysis["priority_distribution"] = self._analyze_priority_distribution(bugs)
            
        elif depth == "comprehensive":
            # Add comprehensive analysis features (includes detailed + more)
            analysis["severity_breakdown"] = self._analyze_severity_patterns(bugs)
            analysis["temporal_patterns"] = self._analyze_temporal_patterns(bugs)
            analysis["priority_distribution"] = self._analyze_priority_distribution(bugs)
            analysis["cross_category_analysis"] = self._analyze_cross_category_patterns(bugs)
            analysis["resolution_analysis"] = self._analyze_resolution_patterns(bugs)
            analysis["impact_assessment"] = self._assess_business_impact(bugs)
            analysis["predictive_insights"] = self._generate_predictive_insights(analysis)
            
        return analysis
    
    def _analyze_severity_patterns(self, bugs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze severity distribution and patterns"""
        severity_data = {}
        for bug in bugs:
            severity = bug.get("severity", "Unknown")
            if severity not in severity_data:
                severity_data[severity] = {
                    "count": 0,
                    "percentage": 0.0,
                    "avg_resolution_time": 0.0,
                    "most_common_area": ""
                }
            severity_data[severity]["count"] += 1
        
        total_bugs = len(bugs)
        for severity, data in severity_data.items():
            data["percentage"] = round((data["count"] / total_bugs) * 100, 1)
        
        return severity_data
    
    def _analyze_temporal_patterns(self, bugs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze when bugs are created and resolved"""
        temporal_patterns = {
            "creation_by_day": {},
            "creation_by_hour": {},
            "resolution_time_trends": {},
            "seasonal_patterns": []
        }
        
        for bug in bugs:
            created_date = bug.get("created_date", "")
            if created_date:
                try:
                    dt = datetime.fromisoformat(created_date.replace("Z", "+00:00"))
                    day_name = dt.strftime("%A")
                    hour = dt.hour
                    
                    temporal_patterns["creation_by_day"][day_name] = temporal_patterns["creation_by_day"].get(day_name, 0) + 1
                    temporal_patterns["creation_by_hour"][str(hour)] = temporal_patterns["creation_by_hour"].get(str(hour), 0) + 1
                except:
                    continue
        
        return temporal_patterns
    
    def _analyze_priority_distribution(self, bugs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze priority distribution and correlations"""
        priority_data = {}
        for bug in bugs:
            priority = bug.get("priority", "Unknown")
            area = bug.get("area_path", "Unknown")
            
            if priority not in priority_data:
                priority_data[priority] = {
                    "count": 0,
                    "areas": {},
                    "percentage": 0.0
                }
            
            priority_data[priority]["count"] += 1
            priority_data[priority]["areas"][area] = priority_data[priority]["areas"].get(area, 0) + 1
        
        total_bugs = len(bugs)
        for priority, data in priority_data.items():
            data["percentage"] = round((data["count"] / total_bugs) * 100, 1)
        
        return priority_data
    
    def _analyze_cross_category_patterns(self, bugs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns across different bug categories"""
        cross_patterns = {
            "category_correlations": {},
            "common_combinations": [],
            "area_category_matrix": {}
        }
        
        # This would analyze which categories tend to appear together
        # For now, return basic structure
        return cross_patterns
    
    def _analyze_resolution_patterns(self, bugs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how bugs are resolved"""
        resolution_patterns = {
            "avg_resolution_time_by_category": {},
            "resolution_success_rate": 0.0,
            "reopen_patterns": {},
            "assignee_efficiency": {}
        }
        
        resolved_bugs = [b for b in bugs if b.get("state") in ["Closed", "Resolved"]]
        resolution_patterns["resolution_success_rate"] = round((len(resolved_bugs) / len(bugs)) * 100, 1) if bugs else 0.0
        
        return resolution_patterns
    
    def _assess_business_impact(self, bugs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess the business impact of bugs"""
        impact_assessment = {
            "customer_facing_bugs": 0,
            "revenue_impact_estimate": "Low",
            "user_experience_impact": "Moderate",
            "system_reliability_score": 85.0,
            "recommended_actions": []
        }
        
        # Calculate customer-facing bugs
        customer_facing = 0
        for bug in bugs:
            area = bug.get("area_path", "").lower()
            tags = [str(tag).lower() for tag in bug.get("tags", [])]
            
            if any(keyword in area for keyword in ["ui", "frontend", "customer"]) or \
               any(keyword in tag for tag in tags for keyword in ["ui", "customer", "frontend"]):
                customer_facing += 1
        
        impact_assessment["customer_facing_bugs"] = customer_facing
        
        # Adjust impact based on bug count and severity
        critical_bugs = len([b for b in bugs if "critical" in str(b.get("severity", "")).lower()])
        if critical_bugs > 0:
            impact_assessment["revenue_impact_estimate"] = "High" if critical_bugs > 5 else "Medium"
        
        return impact_assessment
    
    def _generate_predictive_insights(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate predictive insights based on analysis"""
        insights = []
        
        total_bugs = analysis.get("total_bugs_analyzed", 0)
        categories = analysis.get("categories", {})
        
        # Find trending categories
        category_counts = [(cat, len(bugs)) for cat, bugs in categories.items() if bugs]
        if category_counts:
            top_category, top_count = max(category_counts, key=lambda x: x[1])
            if top_count > total_bugs * 0.4:
                insights.append(f"High concentration in {top_category} suggests systematic issues")
        
        # Predict future trends
        insights.append("Based on current patterns, continued monitoring of top categories is recommended")
        
        return insights

    def _generate_root_cause_recommendation(self, category: str, bug_count: int, analysis_depth: str = "standard") -> Dict[str, str]:
        """Generate specific recommendations for root cause categories"""
        recommendations_map = {
            "System Stability": {
                "focus": "Infrastructure and error handling",
                "action": "Implement comprehensive logging and monitoring",
                "testing": "Add stability and stress testing"
            },
            "API Issues": {
                "focus": "API design and integration testing",
                "action": "Review API contracts and add timeout handling",
                "testing": "Implement API integration test suite"
            },
            "UI/UX Problems": {
                "focus": "Frontend code quality and browser testing",
                "action": "Improve UI component testing and responsive design",
                "testing": "Cross-browser and device testing"
            },
            "Configuration Issues": {
                "focus": "Deployment and environment management",
                "action": "Implement configuration validation and defaults",
                "testing": "Test deployment procedures across environments"
            },
            "Data/Database Issues": {
                "focus": "Data integrity and database performance",
                "action": "Review database queries and add proper indexing",
                "testing": "Add database performance and migration tests"
            }
        }
        
        default_recommendation = {
            "focus": "Code review and testing practices",
            "action": "Implement additional code review processes",
            "testing": "Expand test coverage for affected areas"
        }
        
        recommendation = recommendations_map.get(category, default_recommendation)
        recommendation["category"] = category
        recommendation["affected_bugs"] = bug_count
        
        return recommendation
    
    async def generate_bug_insights(self, bug: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI insights for a specific bug"""
        # Use internal AI if configured
        if settings.use_internal_ai:
            try:
                internal_ai = get_internal_ai_service()
                logger.info("Using Thomson Reuters internal AI for bug insights")
                return await internal_ai.generate_bug_insights(bug)
            except Exception as e:
                logger.warning(f"Internal AI failed, falling back to local analysis: {str(e)}")
        
        insights = {
            "summary": "",
            "likely_cause": "",
            "testing_focus": [],
            "related_areas": [],
            "keywords": []
        }
        
        try:
            # Extract text content
            bug_text = f"{bug.get('title', '')} {bug.get('description', '')}"
            
            # Extract keywords
            insights["keywords"] = self.extract_keywords(bug_text)
            
            # Determine likely cause based on keywords and content
            insights["likely_cause"] = self._determine_likely_cause(bug_text)
            
            # Generate testing recommendations
            insights["testing_focus"] = self._generate_testing_recommendations(bug)
            
            # Identify related areas
            insights["related_areas"] = self._identify_related_areas(bug)
            
            # Generate summary
            insights["summary"] = self._generate_bug_summary(bug)
            
        except Exception as e:
            logger.error(f"Error generating bug insights: {str(e)}")
        
        return insights
    
    def _determine_likely_cause(self, bug_text: str) -> str:
        """Determine likely cause based on bug content"""
        bug_text_lower = bug_text.lower()
        
        if any(term in bug_text_lower for term in ["null", "exception", "error", "crash"]):
            return "Code Error/Exception"
        elif any(term in bug_text_lower for term in ["slow", "timeout", "performance"]):
            return "Performance Issue"
        elif any(term in bug_text_lower for term in ["display", "render", "ui", "button"]):
            return "UI/Frontend Issue"
        elif any(term in bug_text_lower for term in ["api", "service", "connection"]):
            return "Backend/API Issue"
        elif any(term in bug_text_lower for term in ["data", "database", "query"]):
            return "Data/Database Issue"
        else:
            return "General Functionality Issue"
    
    def _generate_testing_recommendations(self, bug: Dict[str, Any]) -> List[str]:
        """Generate testing focus recommendations"""
        recommendations = []
        
        severity = bug.get("severity", "").lower()
        priority = bug.get("priority", "").lower()
        
        if "critical" in severity or "1" in severity:
            recommendations.append("Immediate regression testing required")
            recommendations.append("Test core functionality end-to-end")
        
        if "high" in priority or "1" in priority:
            recommendations.append("Priority testing of affected workflows")
        
        area_path = bug.get("area_path", "").lower()
        if "ui" in area_path or "frontend" in area_path:
            recommendations.append("Cross-browser compatibility testing")
        elif "api" in area_path or "backend" in area_path:
            recommendations.append("API integration testing")
        
        return recommendations[:5]  # Limit to 5 recommendations
    
    def _identify_related_areas(self, bug: Dict[str, Any]) -> List[str]:
        """Identify related system areas that might be affected"""
        areas = []
        
        bug_text = f"{bug.get('title', '')} {bug.get('description', '')}".lower()
        
        area_keywords = {
            "Authentication": ["login", "auth", "password", "token"],
            "Database": ["data", "database", "query", "table"],
            "API": ["api", "endpoint", "service", "request"],
            "UI": ["interface", "button", "page", "display"],
            "Search": ["search", "filter", "query", "results"],
            "Payment": ["payment", "billing", "purchase", "transaction"]
        }
        
        for area, keywords in area_keywords.items():
            if any(keyword in bug_text for keyword in keywords):
                areas.append(area)
        
        return areas
    
    def _generate_bug_summary(self, bug: Dict[str, Any]) -> str:
        """Generate a concise summary of the bug"""
        title = bug.get("title", "")
        state = bug.get("state", "")
        priority = bug.get("priority", "")
        
        summary = f"Bug titled '{title}' "
        
        if state:
            summary += f"is currently {state.lower()}. "
        
        if priority:
            summary += f"Priority level: {priority}. "
        
        return summary


# Global service instance
ai_service = AIService()

def get_ai_service() -> AIService:
    """Get AI service instance"""
    return ai_service
