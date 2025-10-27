# Team Collaboration Guide - AI Bug Analyzer

## 🔐 Security & Sensitive Data Management

### **CRITICAL: Never Commit Sensitive Data**

This repository contains sensitive information that should **NEVER** be committed to git:
- Azure DevOps Personal Access Tokens (PAT)
- Thomson Reuters ESSO tokens
- Organization URLs and project names
- Database credentials
- API keys

### **Protected Files**
The following files are excluded from git tracking via `.gitignore`:
```
backend/.env
backend/.env.*
*.db
*.sqlite*
*pat*
*token*
*secrets*
```

## 🚀 Initial Setup for New Team Members

### **1. Clone Repository**
```bash
git clone <repository-url>
cd ai-bug-analyzer
```

### **2. Run Environment Setup**
```bash
python setup_environment.py
```

### **3. Configure Environment Variables**
```bash
# Copy the example file
cp backend/.env.example backend/.env

# Edit with your credentials
code backend/.env
```

### **4. Required Credentials**

#### **Azure DevOps Setup**
1. Go to Azure DevOps → User Settings → Personal Access Tokens
2. Create new token with **Work Items (Read)** permission
3. Copy token to `ADO_PAT` in `.env`

#### **Thomson Reuters ESSO Token**
1. Navigate to OpenArena User-Details page
2. Click "Copy Bearer Token"
3. Paste token to `ESSO_TOKEN` in `.env`

### **5. Install Dependencies**
```bash
# Backend dependencies
cd backend
pip install -r requirements.txt

# MCP Server dependencies  
cd ../mcp_server
pip install -r requirements.txt
```

## 🔄 Daily Workflow - Pulling Latest Code

### **When You Pull Latest Code, ALWAYS:**

#### **1. Check for Environment Changes**
```bash
git pull origin main

# Compare your .env with the example
diff backend/.env backend/.env.example
```

#### **2. Update Environment Variables**
If new variables are added to `.env.example`, add them to your `.env`:
```bash
# Check what's new in the example
cat backend/.env.example

# Add any missing variables to your .env
echo "NEW_VARIABLE=your-value" >> backend/.env
```

#### **3. Install New Dependencies**
```bash
# Check if requirements changed
git diff HEAD~1 backend/requirements.txt
git diff HEAD~1 mcp_server/requirements.txt

# Install any new dependencies
pip install -r backend/requirements.txt
pip install -r mcp_server/requirements.txt
```

#### **4. Run Environment Validation**
```bash
python setup_environment.py
```

## 📋 Mandatory Details Checklist

### **Before Starting Work:**
- [ ] ✅ Environment variables configured
- [ ] ✅ Dependencies installed
- [ ] ✅ Database accessible
- [ ] ✅ Azure DevOps connection working
- [ ] ✅ ESSO token valid (not expired)

### **Before Committing:**
- [ ] ✅ No sensitive data in commit
- [ ] ✅ `.env` files not tracked
- [ ] ✅ Database files excluded
- [ ] ✅ Code tested locally
- [ ] ✅ Documentation updated if needed

### **Environment Variable Checklist:**
```bash
# Run this to verify all required variables are set
python -c "
import os
from dotenv import load_dotenv
load_dotenv('backend/.env')

required = ['ADO_ORG_URL', 'ADO_PROJECT', 'ADO_PAT', 'ESSO_TOKEN']
missing = [var for var in required if not os.getenv(var) or 'placeholder' in os.getenv(var, '')]
if missing:
    print(f'❌ Missing: {missing}')
else:
    print('✅ All environment variables configured')
"
```

## 🛡️ Security Best Practices

### **Token Management**
- **Rotate tokens regularly** (every 90 days)
- **Use minimum required permissions** 
- **Never share tokens** via chat/email
- **Revoke tokens** when leaving project

### **Environment Files**
- **Never commit `.env` files**
- **Use `.env.example` for templates**
- **Validate environment** before pushing code
- **Keep local `.env` updated** with team changes

### **Code Reviews**
- **Check for hardcoded credentials**
- **Verify `.gitignore` effectiveness** 
- **Validate environment variables**
- **Test with clean environment**

## 🚨 Emergency Procedures

### **If Sensitive Data is Committed:**

#### **1. Immediate Action**
```bash
# Remove from git history (if not pushed yet)
git reset --soft HEAD~1
git reset HEAD backend/.env
rm backend/.env
git commit -m "Remove sensitive data"

# If already pushed - contact team lead immediately
```

#### **2. Token Rotation**
1. **Revoke compromised tokens** in Azure DevOps
2. **Generate new tokens** 
3. **Update team** with new credentials
4. **Verify no unauthorized access**

### **If Environment Setup Fails:**

#### **1. Common Issues**
- **Token expired**: Generate new ESSO token
- **Permissions**: Check Azure DevOps PAT permissions
- **Network**: Verify Zscaler/VPN connection
- **Dependencies**: Clear pip cache and reinstall

#### **2. Debug Steps**
```bash
# Validate environment
python setup_environment.py

# Test Azure DevOps connection
curl -u :$ADO_PAT "$ADO_ORG_URL/$ADO_PROJECT/_apis/wit/workitems?api-version=6.0"

# Test OpenArena connection  
curl -H "Authorization: Bearer $ESSO_TOKEN" $OPEN_ARENA_BASE_URL
```

## 👥 Team Communication

### **New Team Member Onboarding**
1. **Share this guide** before repository access
2. **Verify environment setup** together
3. **Test credentials** in safe environment
4. **Review security practices**

### **Credential Updates**
- **Announce in team chat** when rotating tokens
- **Update documentation** with new requirements
- **Test thoroughly** before team rollout

### **Code Deployment**
- **Never deploy from local** `.env`
- **Use environment-specific** configurations
- **Validate credentials** in target environment
- **Monitor for security alerts**

## 📞 Support & Contacts

### **Technical Issues**
- **Environment Setup**: Run `python setup_environment.py`
- **Azure DevOps**: Check PAT permissions
- **Thomson Reuters**: Verify ESSO token validity

### **Security Concerns**
- **Immediate**: Revoke compromised credentials
- **Team Lead**: Report security incidents
- **IT Security**: For broader security issues

## ✅ Quick Reference Commands

```bash
# Setup new environment
python setup_environment.py

# Validate configuration
python -c "from backend.app.core.config import settings; print('✅ Config loaded')"

# Test services
cd backend && python -m uvicorn app.main:app --reload --port 8000

# Verify git security
git ls-files | grep -E '\.(env|pat|token)$' || echo "✅ No sensitive files tracked"
```

---

**Remember**: Security is everyone's responsibility. When in doubt, ask the team! 🛡️
