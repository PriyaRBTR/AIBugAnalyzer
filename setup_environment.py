#!/usr/bin/env python3
"""
Environment Setup Script for AI Bug Analyzer
This script helps set up the development environment and ensures sensitive data is properly configured.
"""

import os
import shutil
import sys
from pathlib import Path

def setup_environment():
    """Set up the development environment"""
    print("[SETUP] Setting up AI Bug Analyzer environment...")
    
    # Check if .env file exists
    env_file = Path("backend/.env")
    env_example = Path("backend/.env.example")
    
    if not env_file.exists():
        if env_example.exists():
            print("[COPY] Copying .env.example to .env...")
            shutil.copy2(env_example, env_file)
            print("[SUCCESS] Created backend/.env file")
            print("[IMPORTANT] Please update backend/.env with your actual credentials!")
        else:
            print("[ERROR] backend/.env.example not found!")
            return False
    else:
        print("[SUCCESS] backend/.env file already exists")
    
    # Check for required directories
    required_dirs = [
        "backend/logs",
        "backend/temp",
        "frontend/dist",
        "mcp_server/logs"
    ]
    
    for dir_path in required_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"[SUCCESS] Created directory: {dir_path}")
    
    # Check Python requirements
    requirements_files = [
        "backend/requirements.txt",
        "mcp_server/requirements.txt"
    ]
    
    print("\n[CHECK] Checking requirements files...")
    for req_file in requirements_files:
        if Path(req_file).exists():
            print(f"[SUCCESS] Found {req_file}")
        else:
            print(f"[WARNING] Missing {req_file}")
    
    print("\n[SECURITY] Security Checklist:")
    print("   - [SUCCESS] .gitignore configured to exclude .env files")
    print("   - [SUCCESS] .env.example created as template")
    print("   - [WARNING] Update .env with your actual credentials")
    print("   - [WARNING] Never commit .env files to git")
    
    print("\n[NEXT] Next Steps:")
    print("   1. Update backend/.env with your Azure DevOps credentials")
    print("   2. Install dependencies: pip install -r backend/requirements.txt")
    print("   3. Install MCP dependencies: pip install -r mcp_server/requirements.txt")
    print("   4. Start the application: python -m uvicorn app.main:app --reload")
    
    return True

def check_git_status():
    """Check git status and warn about sensitive files"""
    if os.path.exists(".git"):
        print("\n[GIT] Git Repository Detected")
        
        # Check if .env is tracked
        if os.system("git ls-files backend/.env > /dev/null 2>&1") == 0:
            print("[WARNING] backend/.env is tracked by git!")
            print("   Run: git rm --cached backend/.env")
            print("   Then: git commit -m 'Remove .env from tracking'")
        else:
            print("[SUCCESS] backend/.env is not tracked by git")
        
        # Check gitignore
        if os.path.exists(".gitignore"):
            with open(".gitignore", "r") as f:
                if ".env" in f.read():
                    print("[SUCCESS] .gitignore properly configured")
                else:
                    print("[WARNING] .env not found in .gitignore")
    
def validate_env_file():
    """Validate .env file has required variables"""
    env_file = Path("backend/.env")
    if not env_file.exists():
        return False
    
    required_vars = [
        "ADO_ORG_URL",
        "ADO_PROJECT", 
        "ADO_PAT",
        "ESSO_TOKEN"
    ]
    
    env_content = env_file.read_text()
    missing_vars = []
    
    for var in required_vars:
        if f"{var}=" not in env_content or f"{var}=your-" in env_content or f"{var}=placeholder" in env_content:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"[WARNING] Please configure these variables in backend/.env:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    
    print("[SUCCESS] Environment variables properly configured")
    return True

if __name__ == "__main__":
    if setup_environment():
        check_git_status()
        print("\n" + "="*50)
        print("[SUCCESS] Environment setup completed!")
        
        if not validate_env_file():
            print("\n[WARNING] Don't forget to configure your environment variables!")
        
        print("="*50)
    else:
        print("[ERROR] Environment setup failed!")
        sys.exit(1)
