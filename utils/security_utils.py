"""
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
