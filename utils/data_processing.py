"""
Data Processing Utilities for AI Bug Analyzer
Similar to utils in AI-Repository-Analyzer
"""

import re
from typing import List, Dict, Any

class DataProcessor:
    """Data processing utilities for bug analysis"""
    
    @staticmethod
    def clean_bug_text(text: str) -> str:
        """Clean and normalize bug text for AI analysis"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        return text
    
    @staticmethod
    def extract_keywords(text: str) -> List[str]:
        """Extract keywords from bug text"""
        # Simple keyword extraction (can be enhanced with NLP)
        words = re.findall(r'\b\w{3,}\b', text.lower())
        # Remove common stop words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in words if word not in stop_words]
        return list(set(keywords))
