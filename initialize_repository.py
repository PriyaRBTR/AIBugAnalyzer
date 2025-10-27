#!/usr/bin/env python3
"""
Repository Initialization Script for AI Bug Analyzer
This script initializes a new repository similar to AI-Repository-Analyzer with proper security setup.
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, description=""):
    """Run a shell command and return success status"""
    try:
        if description:
            print(f"[RUNNING] {description}...")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[SUCCESS] {description or 'Command'} completed successfully")
            return True
        else:
            print(f"[ERROR] {description or 'Command'} failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] Error running command: {e}")
        return False

def initialize_git_repository():
    """Initialize git repository with proper security settings"""
    print("\n[GIT] Initializing Git Repository...")
    
    # Check if git is already initialized
    if Path(".git").exists():
        print("[SUCCESS] Git repository already initialized")
    else:
        run_command("git init", "Initializing git repository")
    
    # Add gitignore first (most important for security)
    if Path(".gitignore").exists():
        run_command("git add .gitignore", "Adding .gitignore")
        run_command("git commit -m 'Initial commit: Add comprehensive .gitignore for security'", "Committing .gitignore")
    
    # Check if .env is accidentally tracked
    result = subprocess.run("git ls-files backend/.env", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("[WARNING] backend/.env is tracked by git!")
        print("   Run: git rm --cached backend/.env")
        print("   Then: git commit -m 'Remove .env from tracking'")

def create_additional_directories():
    """Create additional directories needed for the repository structure"""
    directories = [
        "analyzers",
        "utils", 
        "scripts",
        "docs",
        "tests",
        "backend/tests",
        "frontend/tests",
        "mcp_server/tests"
    ]
    
    print("\n[DIRS] Creating directory structure...")
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"[SUCCESS] Created: {directory}")

def create_analyzer_templates():
    """Create template files for AI analyzers"""
    print("\n[AI] Creating AI analyzer templates...")
    
    # Base analyzer template
    base_analyzer_content = '''"""
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
'''
    
    # Duplicate detection analyzer
    duplicate_analyzer_content = '''"""
Duplicate Detection Analyzer
AI-powered duplicate bug detection similar to AI-Repository-Analyzer
"""

from .base_analyzer import BaseAnalyzer
from typing import Dict, List, Any

class DuplicateDetectionAnalyzer(BaseAnalyzer):
    """Analyzer for detecting duplicate bugs using AI similarity"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.similarity_threshold = config.get('similarity_threshold', 0.85)
    
    def analyze(self, bugs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze bugs for duplicates using AI semantic similarity
        Similar to expertise mapping in AI-Repository-Analyzer
        """
        # AI-powered duplicate detection logic here
        results = {
            'duplicates_found': [],
            'similarity_scores': {},
            'recommendations': [],
            'analysis_summary': {
                'total_bugs_analyzed': len(bugs),
                'duplicates_detected': 0,
                'confidence_score': 0.0
            }
        }
        
        # TODO: Implement AI similarity analysis
        return results
'''
    
    # Root cause analyzer
    root_cause_content = '''"""
Root Cause Analysis Analyzer
AI-powered root cause analysis similar to AI-Repository-Analyzer
"""

from .base_analyzer import BaseAnalyzer
from typing import Dict, List, Any

class RootCauseAnalyzer(BaseAnalyzer):
    """Analyzer for AI-powered root cause analysis"""
    
    def analyze(self, bug_patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze bug patterns for root causes
        Similar to timeline analysis in AI-Repository-Analyzer
        """
        results = {
            'root_causes': [],
            'pattern_analysis': {},
            'recommendations': [],
            'prevention_strategies': []
        }
        
        # TODO: Implement AI root cause analysis
        return results
'''
    
    # Write analyzer files
    analyzers = {
        'analyzers/base_analyzer.py': base_analyzer_content,
        'analyzers/duplicate_detection.py': duplicate_analyzer_content,
        'analyzers/root_cause_analysis.py': root_cause_content
    }
    
    for filename, content in analyzers.items():
        with open(filename, 'w') as f:
            f.write(content)
        print(f"[SUCCESS] Created: {filename}")

def create_utils_templates():
    """Create utility templates"""
    print("\n[UTILS] Creating utility templates...")
    
    security_utils = '''"""
Security Utilities for AI Bug Analyzer
Enterprise-grade security functions
"""

import os
import hashlib
from typing import Optional, Dict, Any

class SecurityUtils:
    """Security utility functions for sensitive data handling"""
    
    @staticmethod
    def mask_token(token: str, visible_chars: int = 4) -> str:
        """Mask sensitive tokens for logging"""
        if not token or len(token) <= visible_chars:
            return "***"
        return token[:visible_chars] + "***" + token[-visible_chars:]
    
    @staticmethod
    def validate_env_vars(required_vars: list) -> Dict[str, bool]:
        """Validate required environment variables are set"""
        validation_results = {}
        for var in required_vars:
            value = os.getenv(var)
            is_valid = bool(value and not any(placeholder in value.lower() 
                                            for placeholder in ['placeholder', 'your-', 'example']))
            validation_results[var] = is_valid
        return validation_results
    
    @staticmethod
    def generate_session_id() -> str:
        """Generate secure session ID"""
        import uuid
        return str(uuid.uuid4())
'''
    
    data_processing = '''"""
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
        text = re.sub(r'\\s+', ' ', text.strip())
        
        return text
    
    @staticmethod
    def extract_keywords(text: str) -> List[str]:
        """Extract keywords from bug text"""
        # Simple keyword extraction (can be enhanced with NLP)
        words = re.findall(r'\\b\\w{3,}\\b', text.lower())
        # Remove common stop words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in words if word not in stop_words]
        return list(set(keywords))
'''
    
    utils = {
        'utils/security_utils.py': security_utils,
        'utils/data_processing.py': data_processing
    }
    
    for filename, content in utils.items():
        with open(filename, 'w') as f:
            f.write(content)
        print(f"[SUCCESS] Created: {filename}")

def create_init_files():
    """Create __init__.py files for Python packages"""
    init_files = [
        'analyzers/__init__.py',
        'utils/__init__.py',
        'backend/tests/__init__.py',
        'frontend/tests/__init__.py',
        'mcp_server/tests/__init__.py'
    ]
    
    for init_file in init_files:
        Path(init_file).touch()
        print(f"[SUCCESS] Created: {init_file}")

def main():
    """Main initialization function"""
    print("AI Bug Analyzer Repository Initialization")
    print("=" * 50)
    
    # Create directory structure
    create_additional_directories()
    
    # Create analyzer templates
    create_analyzer_templates()
    
    # Create utility templates
    create_utils_templates()
    
    # Create __init__.py files
    create_init_files()
    
    # Initialize git repository
    initialize_git_repository()
    
    print("\n" + "=" * 50)
    print("[SUCCESS] Repository initialization completed!")
    print("\nNext Steps:")
    print("   1. Run: python setup_environment.py")
    print("   2. Configure backend/.env with your credentials")
    print("   3. Install dependencies: pip install -r backend/requirements.txt")
    print("   4. Review TEAM_COLLABORATION_GUIDE.md")
    print("   5. Start development!")
    print("=" * 50)

if __name__ == "__main__":
    main()
