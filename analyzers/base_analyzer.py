"""
Base Analyzer Class for AI Bug Analysis
Similar to AI-Repository-Analyzer structure
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any

class BaseAnalyzer(ABC):
    """Base class for all AI analyzers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    def analyze(self, data: Any) -> Dict[str, Any]:
        """Perform analysis on the provided data"""
        pass
    
    def preprocess_data(self, data: Any) -> Any:
        """Preprocess data before analysis"""
        return data
    
    def postprocess_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Postprocess analysis results"""
        return results
