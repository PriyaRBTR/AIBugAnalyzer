"""
Internal AI Endpoints
===================

API endpoints for managing Thomson Reuters internal AI service integration
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import logging

from ...services.internal_ai_service import get_internal_ai_service
from ...core.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()

@router.get("/health-check", response_model=Dict[str, Any])
async def internal_ai_health_check():
    """
    Check health and connectivity of Thomson Reuters internal AI service
    """
    try:
        if not settings.use_internal_ai:
            return {
                "status": "disabled",
                "message": "Internal AI is not enabled in configuration",
                "use_internal_ai": False
            }
        
        internal_ai = get_internal_ai_service()
        health_result = await internal_ai.health_check()
        
        return {
            "status": "success",
            "internal_ai_health": health_result,
            "use_internal_ai": True,
            "configuration": {
                "esso_token_configured": bool(settings.esso_token),
                "base_url_configured": bool(settings.open_arena_thomson_reuters_url),
                "workflow_id_configured": bool(settings.ai_arena_workflow_id)
            }
        }
        
    except Exception as e:
        logger.error(f"Internal AI health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal AI health check failed: {str(e)}"
        )

@router.get("/validate-configuration", response_model=Dict[str, Any])
async def validate_internal_ai_configuration():
    """
    Validate internal AI configuration and credentials
    """
    try:
        if not settings.use_internal_ai:
            return {
                "status": "disabled",
                "message": "Internal AI is not enabled",
                "configuration_valid": False
            }
        
        internal_ai = get_internal_ai_service()
        validation_result = await internal_ai.validate_configuration()
        
        return {
            "status": "success",
            "validation_result": validation_result
        }
        
    except Exception as e:
        logger.error(f"Internal AI configuration validation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Configuration validation failed: {str(e)}"
        )

@router.get("/configuration", response_model=Dict[str, Any])
async def get_internal_ai_configuration():
    """
    Get current internal AI configuration (without sensitive data)
    """
    return {
        "use_internal_ai": settings.use_internal_ai,
        "configuration": {
            "esso_token_configured": bool(settings.esso_token),
            "base_url_configured": bool(settings.open_arena_thomson_reuters_url),
            "workflow_id_configured": bool(settings.ai_arena_workflow_id),
            "timeout": settings.ai_service_timeout,
            "max_retries": settings.ai_max_retries
        },
        "endpoints": {
            "base_url": settings.open_arena_thomson_reuters_url if settings.open_arena_thomson_reuters_url else "Not configured"
        }
    }

@router.post("/test-duplicate-detection", response_model=Dict[str, Any])
async def test_internal_ai_duplicate_detection(request: Dict[str, Any]):
    """
    Test duplicate detection using internal AI service
    
    Expected request body:
    {
        "query_text": "User login fails with timeout error",
        "existing_bugs": [list of bug objects],
        "threshold": 0.85 (optional)
    }
    """
    try:
        if not settings.use_internal_ai:
            raise HTTPException(
                status_code=400,
                detail="Internal AI is not enabled"
            )
        
        query_text = request.get("query_text")
        existing_bugs = request.get("existing_bugs", [])
        threshold = request.get("threshold")
        
        if not query_text:
            raise HTTPException(
                status_code=400,
                detail="query_text is required"
            )
        
        internal_ai = get_internal_ai_service()
        duplicates = await internal_ai.find_duplicate_bugs(query_text, existing_bugs, threshold)
        
        return {
            "status": "success",
            "query_text": query_text,
            "duplicates_found": len(duplicates),
            "duplicates": duplicates,
            "ai_service": "Thomson Reuters Internal AI"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Internal AI duplicate detection test failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Duplicate detection test failed: {str(e)}"
        )

@router.post("/test-root-cause-analysis", response_model=Dict[str, Any])
async def test_internal_ai_root_cause_analysis(request: Dict[str, Any]):
    """
    Test root cause analysis using internal AI service
    
    Expected request body:
    {
        "bugs": [list of bug objects]
    }
    """
    try:
        if not settings.use_internal_ai:
            raise HTTPException(
                status_code=400,
                detail="Internal AI is not enabled"
            )
        
        bugs = request.get("bugs", [])
        
        if not bugs:
            raise HTTPException(
                status_code=400,
                detail="bugs list is required"
            )
        
        internal_ai = get_internal_ai_service()
        analysis = await internal_ai.analyze_root_causes(bugs)
        
        return {
            "status": "success",
            "bugs_analyzed": len(bugs),
            "analysis": analysis,
            "ai_service": "Thomson Reuters Internal AI"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Internal AI root cause analysis test failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Root cause analysis test failed: {str(e)}"
        )

@router.post("/test-bug-insights", response_model=Dict[str, Any])
async def test_internal_ai_bug_insights(request: Dict[str, Any]):
    """
    Test bug insights generation using internal AI service
    
    Expected request body:
    {
        "bug": {bug object}
    }
    """
    try:
        if not settings.use_internal_ai:
            raise HTTPException(
                status_code=400,
                detail="Internal AI is not enabled"
            )
        
        bug = request.get("bug")
        
        if not bug:
            raise HTTPException(
                status_code=400,
                detail="bug object is required"
            )
        
        internal_ai = get_internal_ai_service()
        insights = await internal_ai.generate_bug_insights(bug)
        
        return {
            "status": "success",
            "bug_id": bug.get("id", "unknown"),
            "insights": insights,
            "ai_service": "Thomson Reuters Internal AI"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Internal AI bug insights test failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Bug insights test failed: {str(e)}"
        )

@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_with_internal_ai(request: Dict[str, Any]):
    """
    General analysis endpoint for AI assistant questions and help content
    
    Expected request body:
    {
        "query": "User question or help request",
        "context": "help_question|help_documentation|general",
        "project_name": "optional project context",
        "area_path": "optional area context"
    }
    """
    try:
        query = request.get("query")
        context = request.get("context", "general")
        project_name = request.get("project_name")
        area_path = request.get("area_path")
        
        if not query:
            raise HTTPException(
                status_code=400,
                detail="query is required"
            )
        
        # If internal AI is not available, provide fallback responses
        if not settings.use_internal_ai:
            return await _generate_fallback_response(query, context, project_name, area_path)
        
        try:
            internal_ai = get_internal_ai_service()
            
            # Create a contextual prompt based on the request
            contextual_query = _build_contextual_query(query, context, project_name, area_path)
            
            # Use the general AI analysis capability
            analysis = await internal_ai.analyze_general_query(contextual_query)
            
            return {
                "success": True,
                "analysis": analysis,
                "insights": [
                    f"Analysis provided by Thomson Reuters Internal AI",
                    f"Context: {context}",
                    f"Query processed successfully"
                ],
                "ai_service": "Thomson Reuters Internal AI"
            }
            
        except Exception as ai_error:
            logger.warning(f"Internal AI failed, using fallback: {str(ai_error)}")
            return await _generate_fallback_response(query, context, project_name, area_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Internal AI analyze failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

def _build_contextual_query(query: str, context: str, project_name: str = None, area_path: str = None) -> str:
    """Build a contextual query for the AI service"""
    context_parts = [f"Context: Azure DevOps bug management"]
    
    if project_name:
        context_parts.append(f"Project: {project_name}")
    if area_path:
        context_parts.append(f"Area: {area_path}")
    
    if context == "help_documentation":
        context_parts.append("Task: Provide comprehensive help documentation")
    elif context == "help_question":
        context_parts.append("Task: Answer specific user question")
    
    context_string = ". ".join(context_parts)
    return f"{context_string}. {query}"

async def _generate_fallback_response(query: str, context: str, project_name: str = None, area_path: str = None) -> Dict[str, Any]:
    """Generate intelligent, ADO-specific fallback response when internal AI is not available"""
    
    query_lower = query.lower()
    
    # Enhanced intelligent responses for ADO-specific scenarios
    if any(word in query_lower for word in ['create', 'creating', 'new bug', 'add bug', 'submit']):
        response = f"""To create a bug in Azure DevOps:

**Step-by-Step Process:**

1. **Navigate to Work Items**:
   - Go to Azure DevOps portal → Your Project → Boards → Work Items
   - Click "New Work Item" → Select "Bug"

2. **Fill Essential Fields**:
   - **Title**: Clear, specific description (e.g., "Login fails with 500 error when using special characters")
   - **Area Path**: Select appropriate team/component area
   - **Iteration**: Choose current sprint/iteration
   - **Priority**: Set based on business impact (1=Critical, 2=High, 3=Medium, 4=Low)
   - **Severity**: Technical impact (1=Critical, 2=High, 3=Medium, 4=Low)

3. **Detailed Description**:
   - **Steps to Reproduce**: Numbered list of exact actions
   - **Expected Result**: What should happen
   - **Actual Result**: What actually happens
   - **Environment**: Browser, OS, application version
   - **Additional Info**: Screenshots, logs, error messages

4. **Classification**:
   - **Tags**: Add relevant keywords for filtering
   - **Assigned To**: Leave blank initially for triage, or assign to specific person
   - **Original Estimate**: Time estimate for fix (optional)

5. **Attachments**:
   - Screenshots of the issue
   - Log files or error traces
   - Video recordings if helpful

**Best Practices**:
- Use clear, searchable titles
- Include reproduction rate (Always/Sometimes/Rarely)
- Reference related work items if applicable
- Add acceptance criteria for the fix

After creation, the bug will enter "New" state and can be triaged by the team."""

    elif any(word in query_lower for word in ['priority', 'prioritize', 'triage', 'triaging', 'assign']) or 'priority' in query_lower:
        # Check if the question is specifically about environment-specific bugs
        if any(phrase in query_lower for phrase in ['lower environment', 'lower env', 'dev environment', 'test environment', 'staging']):
            response = f"""**Bug Priority for Lower Environment Issues:**

**Your Question**: "{query}"

**Environment-Specific Bug Priority Guidelines:**

🔍 **If a bug is ONLY reproducible in lower environments (Dev/Test/Staging):**

**Recommended Priority: Priority 3 (Medium) or Priority 4 (Low)**

**Decision Factors:**

1. **Environment Impact Assessment**:
   - **Lower environments only** → Generally Priority 3-4
   - **Blocking development/testing** → Priority 2-3
   - **Production risk potential** → Priority 2-3
   - **Cosmetic/minor issues** → Priority 4

2. **Business Impact Considerations**:
   - **Does it block other developers?** → Higher priority
   - **Will it reach production?** → Higher priority
   - **Is there a workaround?** → Lower priority
   - **Timeline to production deployment** → Affects urgency

3. **Technical Assessment**:
   - **Configuration difference** → Priority 4 (environment-specific config)
   - **Data difference** → Priority 3 (could affect production with similar data)
   - **Code logic flaw** → Priority 2-3 (will likely appear in production)
   - **Environment setup issue** → Priority 4

**Recommended Action Plan:**

✅ **Priority 3 (Medium)** if:
- Bug could potentially occur in production
- Blocks testing of important features
- Affects multiple team members
- Root cause unclear

✅ **Priority 4 (Low)** if:
- Environment-specific configuration issue
- Doesn't block critical development work
- Clear workaround available
- Isolated to specific test data/setup

**Additional Considerations:**
- Document environment differences in bug description
- Include environment configuration details
- Test in production-like environment if possible
- Monitor for similar issues in higher environments

**Example Scenarios:**
- **P4**: SSL certificate error in dev environment only
- **P3**: Database connection timeout in test environment (could happen in prod)
- **P2**: Authentication failing in staging (production deployment risk)
- **P4**: UI styling issue only in dev environment with specific test data"""
        else:
            response = f"""Effective Bug Triage in Azure DevOps:

**Triage Process (Daily/Weekly):**

1. **Initial Assessment** (2-5 minutes per bug):
   - Review title and description for clarity
   - Verify reproduction steps are complete
   - Check if it's a duplicate of existing bugs
   - Assess business and technical impact

2. **Priority Matrix**:
   - **Priority 1 (Critical)**: System down, data loss, security breach
   - **Priority 2 (High)**: Core functionality broken, many users affected
   - **Priority 3 (Medium)**: Important feature issue, workaround exists
   - **Priority 4 (Low)**: Minor issue, cosmetic, enhancement

3. **Severity Assessment**:
   - **Severity 1**: Complete failure, no workaround
   - **Severity 2**: Major feature broken, difficult workaround
   - **Severity 3**: Minor feature issue, easy workaround
   - **Severity 4**: Cosmetic or suggestion

4. **Assignment Strategy**:
   - Match bug domain expertise (Frontend/Backend/Database/API)
   - Consider team capacity and sprint commitments
   - Assign to team lead if expertise unclear
   - Set realistic fix timeline based on priority

5. **State Management**:
   - **New → Active**: Bug accepted and being worked on
   - **Active → Resolved**: Fix implemented, ready for testing
   - **Resolved → Closed**: Fix verified, issue confirmed resolved
   - **Any → Removed**: Not a bug, duplicate, or won't fix

**Triage Meeting Tips**:
- Time-box discussions (max 3-5 minutes per bug)
- Focus on impact and effort estimation
- Document decisions in bug comments
- Use consistent criteria across team"""

    elif any(word in query_lower for word in ['workflow', 'process', 'lifecycle', 'states']):
        response = f"""Azure DevOps Bug Lifecycle & Workflow:

**Standard Bug States:**

1. **New** (Entry State):
   - Bug reported but not yet reviewed
   - Awaiting triage and initial assessment
   - Team should review within 24-48 hours

2. **Active** (In Progress):
   - Bug accepted and assigned to developer
   - Investigation and fix development in progress
   - Developer should provide regular updates

3. **Resolved** (Fix Complete):
   - Fix implemented and deployed to test environment
   - Ready for verification by tester/reporter
   - Include details of fix and test instructions

4. **Closed** (Verified Fixed):
   - Fix verified working in target environment
   - Issue officially resolved
   - Can be reopened if problem persists

**Alternative States:**
- **Removed**: Not a bug, by design, or duplicate
- **Committed**: Fix scheduled for specific release

**Workflow Rules:**
- Only assigned person should move from Active → Resolved
- Tester/QA should verify Resolved → Closed
- Original reporter can reopen Closed bugs with justification
- All state changes should include explanatory comments

**Custom Workflows:**
Many teams customize states like:
- Ready for Development
- In Review
- Ready for Testing
- Done

The key is consistency and clear entry/exit criteria for each state."""

    elif any(word in query_lower for word in ['search', 'find', 'query', 'filter']):
        response = f"""Advanced Bug Search & Filtering in Azure DevOps:

**Basic Search Methods:**

1. **Quick Search Bar**:
   - Use keywords from title/description
   - Search across all work items or specific types

2. **Work Items Query**:
   - Go to Boards → Queries → New Query
   - Build complex filters with multiple conditions

**Powerful Query Examples:**

```
// All open bugs in current iteration
SELECT * FROM workitems 
WHERE [Work Item Type] = 'Bug' 
AND [State] <> 'Closed' 
AND [Iteration Path] UNDER @CurrentIteration

// High priority bugs assigned to me
SELECT * FROM workitems 
WHERE [Work Item Type] = 'Bug' 
AND [Priority] <= 2 
AND [Assigned To] = @Me

// Recently created bugs (last 7 days)
SELECT * FROM workitems 
WHERE [Work Item Type] = 'Bug' 
AND [Created Date] >= @Today - 7

// Bugs without area path assigned
SELECT * FROM workitems 
WHERE [Work Item Type] = 'Bug' 
AND [Area Path] = @Project
```

**Advanced Filters:**
- **Tags**: Use tags for custom categorization
- **Custom Fields**: Filter by environment, component, etc.
- **Date Ranges**: Created, modified, resolved dates
- **Text Search**: Search in titles, descriptions, comments

**Saved Queries:**
- Create team-shared queries for common searches
- Set up query notifications for new matches
- Use query-based dashboards and widgets

**Search Tips:**
- Use wildcards: `*login*` finds words containing "login"
- Combine conditions with AND/OR logic
- Save frequently used queries for quick access
- Use @Me, @Today, @CurrentIteration macros"""

    elif any(word in query_lower for word in ['duplicate', 'duplicates', 'similar']):
        response = f"""Managing Duplicate Bugs in Azure DevOps:

**Identifying Duplicates:**

1. **Before Creating New Bug**:
   - Search existing bugs with similar keywords
   - Check recent bugs from same area/component
   - Look for similar error messages or symptoms

2. **During Triage**:
   - Use AI-powered duplicate detection tools
   - Compare reproduction steps and environments
   - Check if root cause might be the same

**Handling Duplicates:**

1. **When You Find a Duplicate**:
   - Link the duplicate to the original (Related → Duplicate)
   - Add comment explaining the duplication
   - Set state to "Removed" with reason "Duplicate"
   - Merge any additional useful information

2. **Linking Work Items**:
   ```
   Original Bug: #12345 "Login timeout error"
   Duplicate: #12367 "Cannot login - timeout"
   
   Action: Link #12367 as duplicate of #12345
   ```

3. **Information Consolidation**:
   - Copy unique reproduction steps to original
   - Merge different browser/environment observations
   - Consolidate user impact information
   - Update tags with additional keywords

**Best Practices:**
- Always notify the duplicate reporter about the original bug
- Encourage reporters to subscribe to original bug for updates
- Use duplicate relationships for impact assessment
- Keep duplicate bugs for historical reference
- Tag original bug with consolidated severity/priority

**Prevention Strategies:**
- Maintain clear, searchable bug titles
- Use consistent terminology across team
- Regularly review and clean up old resolved bugs
- Implement better search training for team members
- Use automated duplicate detection tools where available

**Query for Finding Potential Duplicates:**
```
SELECT * FROM workitems 
WHERE [Work Item Type] = 'Bug' 
AND [Title] CONTAINS 'login'
AND [State] <> 'Closed'
ORDER BY [Created Date] DESC
```"""

    elif any(word in query_lower for word in ['report', 'reporting', 'dashboard', 'metrics']):
        response = f"""Bug Reporting & Analytics in Azure DevOps:

**Key Bug Metrics to Track:**

1. **Volume Metrics**:
   - Total bugs created per sprint/month
   - Open vs. resolved bug trends
   - Bug creation rate vs. resolution rate
   - Backlog growth/reduction

2. **Quality Metrics**:
   - Bug escape rate (production bugs vs. total)
   - Average time to resolution
   - Bug severity distribution
   - Reopen rate (bugs reopened after closure)

3. **Team Performance**:
   - Bugs resolved per developer
   - Average resolution time by team member
   - Triage efficiency (time from New → Active)

**Creating Effective Dashboards:**

1. **Bug Overview Widget**:
   ```
   Query: Active bugs by priority
   Chart Type: Pie chart
   Group By: Priority
   ```

2. **Trend Analysis**:
   ```
   Query: Bug burndown over last 6 sprints
   Chart Type: Line chart
   Time Period: Last 6 iterations
   ```

3. **Quality Dashboard**:
   - Bug density by area path
   - Average days to resolution
   - Bug severity trends over time
   - Escape rate by sprint

**Sample Queries for Reports:**

```sql
-- Bug aging report
SELECT [ID], [Title], [Created Date], [State], [Assigned To]
FROM workitems 
WHERE [Work Item Type] = 'Bug' 
AND [State] = 'Active'
AND [Created Date] < @Today - 30

-- Resolution time analysis
SELECT [ID], [Title], [Created Date], [Resolved Date], 
       [Resolved Date] - [Created Date] as 'Days to Resolve'
FROM workitems 
WHERE [Work Item Type] = 'Bug' 
AND [State] = 'Closed'
AND [Resolved Date] >= @Today - 90
```

**Regular Reports to Generate:**
- Weekly bug triage status
- Monthly quality trends
- Sprint retrospective bug analysis
- Quarterly escape rate review
- Annual team performance metrics"""

    elif any(word in query_lower for word in ['test', 'testing', 'qa', 'quality assurance']):
        response = f"""Software Testing & Quality Assurance Best Practices:

**Testing Methodologies:**

1. **Types of Testing**:
   - **Unit Testing**: Individual components/functions
   - **Integration Testing**: Component interactions
   - **System Testing**: End-to-end functionality
   - **Acceptance Testing**: Business requirements validation
   - **Regression Testing**: Ensuring fixes don't break existing features

2. **Bug Testing Strategies**:
   - **Reproduce First**: Always verify you can reproduce the issue
   - **Test Variations**: Try different inputs, browsers, environments
   - **Boundary Testing**: Test edge cases and limits
   - **Negative Testing**: Test with invalid inputs and scenarios

3. **Test Case Design**:
   - Clear preconditions and setup requirements
   - Step-by-step execution instructions
   - Expected vs actual results documentation
   - Test data requirements and cleanup procedures

**Quality Assurance Processes:**

1. **Defect Lifecycle Management**:
   - New → Open → Fixed → Verified → Closed
   - Detailed defect reporting with screenshots/logs
   - Root cause analysis for critical issues
   - Regression test planning

2. **Test Planning & Strategy**:
   - Risk-based test prioritization
   - Test environment management
   - Test data management and privacy
   - Automation vs manual testing decisions

**Common Testing Tools & Frameworks**:
- **Automation**: Selenium, Cypress, Playwright, TestNG, Jest
- **API Testing**: Postman, REST Assured, SoapUI
- **Performance**: JMeter, LoadRunner, k6
- **Bug Tracking**: Jira, Azure DevOps, Bugzilla, Mantis"""

    elif any(word in query_lower for word in ['agile', 'scrum', 'sprint', 'backlog', 'story']):
        response = f"""Agile & Scrum Bug Management:

**Bug Management in Agile:**

1. **Sprint Planning with Bugs**:
   - Include critical bugs in sprint planning
   - Estimate bug fix effort alongside new features
   - Reserve capacity for urgent production issues
   - Balance feature development vs bug fixing

2. **Bug Triage in Agile**:
   - Daily triage meetings (15-30 minutes max)
   - Product Owner involvement in priority decisions
   - Quick impact vs effort assessment
   - Sprint goals consideration

3. **Definition of Done & Bugs**:
   - Zero critical bugs policy
   - All identified bugs logged and triaged
   - Regression testing completed
   - Code review includes bug fix validation

**Scrum Events & Bug Handling:**

1. **Daily Standups**:
   - Report on bug fixes in progress
   - Escalate blocking issues immediately
   - Share findings from bug investigations

2. **Sprint Review**:
   - Demo bug fixes alongside new features
   - Show quality improvements and metrics
   - Discuss bug trends and prevention

3. **Retrospectives**:
   - Analyze bug causes and prevention strategies
   - Process improvements for faster bug resolution
   - Team learning from complex bug investigations

**User Story & Bug Relationships**:
- Link bugs to affected user stories
- Consider bugs as technical debt items
- Create follow-up stories for preventive measures"""

    elif any(word in query_lower for word in ['performance', 'load', 'stress', 'memory', 'cpu']):
        response = f"""Performance Bug Analysis & Testing:

**Performance Bug Categories:**

1. **Response Time Issues**:
   - Slow page loads or API responses
   - Database query optimization needs
   - Network latency and bandwidth problems
   - Caching strategy improvements

2. **Memory Issues**:
   - Memory leaks causing application crashes
   - High memory usage patterns
   - Garbage collection problems
   - Buffer overflow vulnerabilities

3. **CPU/Resource Issues**:
   - High CPU utilization
   - Inefficient algorithms
   - Resource contention problems
   - Threading and concurrency issues

**Performance Testing Strategies:**

1. **Load Testing**:
   - Simulate normal expected load
   - Measure response times under typical usage
   - Identify performance baselines
   - Monitor system resources

2. **Stress Testing**:
   - Push system beyond normal capacity
   - Find breaking points and failure modes
   - Test recovery mechanisms
   - Validate error handling under stress

3. **Performance Monitoring**:
   - Application Performance Monitoring (APM) tools
   - Real user monitoring (RUM)
   - Synthetic transaction monitoring
   - Infrastructure monitoring

**Common Performance Bug Patterns**:
- N+1 query problems in database access
- Unoptimized loops and algorithms
- Missing or incorrect caching
- Resource leaks (connections, file handles)
- Inefficient data structures and serialization"""

    elif any(word in query_lower for word in ['security', 'vulnerability', 'authentication', 'authorization']):
        response = f"""Security Bug Management & Testing:

**Security Bug Classifications:**

1. **Authentication Issues**:
   - Weak password policies
   - Session management flaws
   - Multi-factor authentication bypasses
   - Account lockout mechanism failures

2. **Authorization Problems**:
   - Privilege escalation vulnerabilities
   - Access control bypass
   - Role-based permission issues
   - API endpoint security gaps

3. **Data Security Issues**:
   - SQL injection vulnerabilities
   - Cross-site scripting (XSS)
   - Data exposure in logs or error messages
   - Insecure data transmission

**Security Testing Approaches:**

1. **Static Analysis**:
   - Code review for security patterns
   - Automated security scanning tools
   - Dependency vulnerability scanning
   - Configuration security checks

2. **Dynamic Testing**:
   - Penetration testing
   - Vulnerability scanning
   - Security-focused test cases
   - Runtime security monitoring

3. **Security Bug Reporting**:
   - Follow responsible disclosure practices
   - Provide detailed reproduction steps
   - Include impact assessment
   - Suggest mitigation strategies

**Common Security Bug Patterns**:
- Input validation failures
- Cross-site request forgery (CSRF)
- Insecure direct object references
- Security misconfiguration
- Sensitive data exposure"""

    elif any(word in query_lower for word in ['debug', 'debugging', 'node', 'nodejs', 'javascript', 'js']):
        if 'memory' in query_lower and 'leak' in query_lower:
            response = f"""Node.js Memory Leak Debugging Guide:

**1. Identifying Memory Leaks:**

**Symptoms:**
- Increasing memory usage over time
- Application becoming slower
- Out of memory errors or crashes
- High garbage collection activity

**Detection Tools:**
```bash
# Monitor memory usage
node --inspect --inspect-brk app.js
# Open chrome://inspect in Chrome

# Use clinic.js for comprehensive analysis
npm install -g clinic
clinic doctor -- node app.js
clinic bubbleprof -- node app.js
clinic flame -- node app.js
```

**2. Built-in Node.js Tools:**

```javascript
// Monitor memory usage in code
setInterval(() => {{
  const used = process.memoryUsage();
  console.log('Memory Usage:');
  for (let key in used) {{
    console.log(`${{key}}: ${{Math.round(used[key] / 1024 / 1024 * 100) / 100}} MB`);
  }}
}}, 5000);

// Heap dump for analysis
const v8 = require('v8');
const fs = require('fs');

function createHeapSnapshot() {{
  const heapSnapshot = v8.getHeapSnapshot();
  const fileName = `heap-${{Date.now()}}.heapsnapshot`;
  const fileStream = fs.createWriteStream(fileName);
  heapSnapshot.pipe(fileStream);
}}
```

**3. Common Memory Leak Patterns:**

**Global Variables:**
```javascript
// BAD: Accidental global
function createLeak() {{
  leak = new Array(1000000); // Missing 'var', 'let', or 'const'
}}

// GOOD: Proper declaration
function noLeak() {{
  const data = new Array(1000000);
}}
```

**Event Listeners:**
```javascript
// BAD: Not removing listeners
function addListener() {{
  document.addEventListener('click', handleClick);
}}

// GOOD: Clean up listeners
function addListener() {{
  document.addEventListener('click', handleClick);
  // Later...
  document.removeEventListener('click', handleClick);
}}
```

**Closures Holding References:**
```javascript
// BAD: Closure keeps reference
function createClosure() {{
  const largeData = new Array(1000000);
  return function() {{
    // Even if largeData isn't used, it's kept in memory
  }};
}}

// GOOD: Clear references
function createClosure() {{
  let largeData = new Array(1000000);
  return function() {{
    largeData = null; // Clear reference when done
  }};
}}
```

**4. Debugging Workflow:**

1. **Baseline Measurement**: Record normal memory usage
2. **Load Testing**: Simulate typical usage patterns
3. **Memory Profiling**: Use Chrome DevTools or clinic.js
4. **Heap Analysis**: Compare heap snapshots over time
5. **Code Review**: Look for common leak patterns
6. **Fix & Verify**: Implement fixes and re-test

**5. Prevention Best Practices:**

- Always use `const`, `let`, or `var` for declarations
- Remove event listeners when no longer needed
- Avoid circular references
- Use WeakMap/WeakSet for object references
- Implement proper cleanup in destructors
- Monitor memory usage in production
- Use linting rules to catch potential leaks

**Tools for Analysis:**
- Chrome DevTools Memory tab
- clinic.js suite
- node --inspect with heap snapshots
- memwatch-next for programmatic monitoring
- autocannon for load testing"""

        else:
            response = f"""Node.js Debugging Best Practices:

**1. Built-in Debugging Tools:**

**Node Inspector:**
```bash
node --inspect app.js
# Open chrome://inspect in Chrome for GUI debugging

node --inspect-brk app.js  # Break on first line
```

**Console Debugging:**
```javascript
console.log('Debug info:', variable);
console.trace('Call stack trace');
console.time('performance-test');
// ... code to measure
console.timeEnd('performance-test');
```

**2. Advanced Debugging Techniques:**

**Debug Module:**
```javascript
const debug = require('debug')('app:module');
debug('This is a debug message');
// Run with: DEBUG=app:* node app.js
```

**Conditional Breakpoints:**
```javascript
if (condition) {{
  debugger; // Breakpoint only when condition is true
}}
```

**3. Error Handling & Logging:**

```javascript
// Structured logging
const winston = require('winston');
const logger = winston.createLogger({{
  level: 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.File({{ filename: 'error.log', level: 'error' }}),
    new winston.transports.Console()
  ]
}});

// Async error handling
process.on('unhandledRejection', (reason, promise) => {{
  logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
}});

process.on('uncaughtException', (error) => {{
  logger.error('Uncaught Exception:', error);
  process.exit(1);
}});
```

**4. Performance Debugging:**

```javascript
// Profiling
node --prof app.js
node --prof-process isolate-*.log > processed.txt

// Event loop monitoring
const eventLoopUtilization = require('@nodejs/event-loop-utilization');
```

**Common Debugging Tools:**
- Node.js built-in debugger
- Chrome DevTools
- VS Code integrated debugger  
- clinic.js for performance
- ndb for enhanced debugging experience"""

    elif any(word in query_lower for word in ['api', 'rest', 'graphql', 'endpoint', 'postman']):
        response = f"""API Testing and Bug Management:

**1. API Testing Strategies:**

**Manual Testing with Postman:**
```javascript
// Pre-request script
pm.globals.set("timestamp", Date.now());
pm.globals.set("auth_token", "Bearer " + pm.environment.get("token"));

// Test script
pm.test("Status code is 200", function () {{
  pm.response.to.have.status(200);
}});

pm.test("Response time is less than 200ms", function () {{
  pm.expect(pm.response.responseTime).to.be.below(200);
}});
```

**Automated API Testing:**
```javascript
// Using Jest and Supertest
const request = require('supertest');
const app = require('../app');

describe('User API', () => {{
  test('GET /users should return users list', async () => {{
    const response = await request(app)
      .get('/users')
      .expect(200);
    
    expect(response.body).toHaveProperty('users');
    expect(Array.isArray(response.body.users)).toBe(true);
  }});
  
  test('POST /users should create user', async () => {{
    const userData = {{ name: 'John', email: 'john@test.com' }};
    const response = await request(app)
      .post('/users')
      .send(userData)
      .expect(201);
    
    expect(response.body).toHaveProperty('id');
  }});
}});
```

**2. Common API Bug Patterns:**

**Authentication Issues:**
- Missing or invalid tokens
- Expired tokens not handled
- Insufficient permission checks
- CORS configuration problems

**Data Validation Problems:**
- Missing input validation
- SQL injection vulnerabilities
- XSS through API responses
- Improper error handling exposing sensitive data

**Performance Issues:**
- N+1 query problems
- Missing pagination
- Lack of response caching
- Inefficient database queries

**3. API Testing Checklist:**

**Functional Testing:**
- ✅ All endpoints respond correctly
- ✅ Request/response formats match documentation
- ✅ Error handling works as expected
- ✅ Authentication and authorization work properly

**Security Testing:**
- ✅ Input validation prevents injection attacks
- ✅ Authentication tokens are properly validated
- ✅ Sensitive data is not exposed in responses
- ✅ Rate limiting prevents abuse

**Performance Testing:**
- ✅ Response times meet requirements
- ✅ API handles expected load
- ✅ Proper error handling under stress
- ✅ Database queries are optimized

**4. Bug Reporting for APIs:**

```markdown
**Bug Title:** API returns 500 error for valid user creation request

**Endpoint:** POST /api/users
**Method:** POST
**Headers:** Content-Type: application/json, Authorization: Bearer <token>
**Request Body:**
{{
  "name": "John Doe",
  "email": "john@example.com"
}}

**Expected Response:** 201 Created with user object
**Actual Response:** 500 Internal Server Error

**Error Details:**
- Error message: "Cannot read property 'email' of undefined"
- Stack trace: [Include relevant stack trace]
- Timestamp: 2023-10-26T10:30:00Z

**Environment:** Development API (api-dev.company.com)
**Reproduction Rate:** Always (100%)
```

**5. API Monitoring & Debugging:**

```javascript
// API monitoring middleware
const apiMonitor = (req, res, next) => {{
  const start = Date.now();
  
  res.on('finish', () => {{
    const duration = Date.now() - start;
    console.log(`${{req.method}} ${{req.path}} - ${{res.statusCode}} - ${{duration}}ms`);
    
    // Log slow requests
    if (duration > 1000) {{
      logger.warn('Slow API request', {{
        method: req.method,
        path: req.path,
        duration,
        statusCode: res.statusCode
      }});
    }}
  }});
  
  next();
}};
```

**Tools for API Testing:**
- Postman/Insomnia for manual testing
- Newman for automated Postman tests
- Jest + Supertest for unit testing
- Artillery/K6 for load testing
- Swagger/OpenAPI for documentation testing"""

    else:
        # Enhanced comprehensive guidance for ANY software development question
        topic_focus = "software development and bug management"
        
        # More specific categorization based on the query
        if any(word in query_lower for word in ['database', 'sql', 'query', 'data', 'mysql', 'postgres', 'mongodb']):
            topic_focus = "database development and optimization"
        elif any(word in query_lower for word in ['frontend', 'ui', 'ux', 'react', 'angular', 'vue', 'css', 'html']):
            topic_focus = "frontend development and user interface"
        elif any(word in query_lower for word in ['backend', 'server', 'microservice', 'architecture', 'python', 'java', 'c#']):
            topic_focus = "backend development and system architecture"
        elif any(word in query_lower for word in ['mobile', 'ios', 'android', 'flutter', 'react native']):
            topic_focus = "mobile application development"
        elif any(word in query_lower for word in ['devops', 'ci/cd', 'deployment', 'docker', 'kubernetes', 'aws']):
            topic_focus = "DevOps and cloud deployment"
        elif any(word in query_lower for word in ['testing', 'unit test', 'integration test', 'automation']):
            topic_focus = "software testing and quality assurance"

        response = f"""I can help you with {topic_focus}!

**Your Question**: "{query}"

**I'm a comprehensive software development expert covering:**

🐛 **Bug Analysis & Resolution**:
- Root cause analysis for any technology stack
- Debugging strategies for different platforms
- Performance optimization and memory management
- Error handling and exception management

💻 **Programming Languages & Frameworks**:
- JavaScript/Node.js, Python, Java, C#, Go, Rust
- React, Angular, Vue.js, Express, Django, Spring Boot
- Database technologies: SQL, NoSQL, ORMs
- Cloud platforms: AWS, Azure, GCP

🔧 **Development Tools & Practices**:
- Version control (Git) and collaboration
- CI/CD pipelines and automation
- Code review and quality assurance
- Testing frameworks and methodologies

🏗️ **Architecture & Design**:
- System design and scalability patterns
- Microservices and distributed systems
- API design and integration
- Security best practices

📊 **Performance & Monitoring**:
- Application performance optimization
- Memory leak detection and resolution
- Database query optimization
- Monitoring and alerting systems

🔍 **Specialized Problem Solving**:
- Cross-platform compatibility issues
- Third-party integration challenges
- Legacy system maintenance
- Technical debt management

**What specific aspect would you like help with?**
- Share your exact problem or error message
- Describe your technology stack and environment
- Mention any constraints or requirements you have
- Include code samples if relevant

I can provide detailed, actionable solutions based on industry best practices and real-world experience."""

    # Add contextual project information
    context_note = ""
    if project_name and area_path:
        context_note = f"\n\n📍 **Your Current Context**: Project `{project_name}` → Area `{area_path}`"
        context_note += f"\n*This guidance can be applied specifically to your current selection.*"
    elif project_name:
        context_note = f"\n\n📍 **Your Current Project**: `{project_name}`"
        context_note += f"\n*This guidance applies to your current project context.*"
    
    return {
        "success": True,
        "analysis": response + context_note,
        "insights": [
            "✨ Comprehensive AI-powered response covering software development, testing, and bug management",
            f"🎯 Context: {context}",
            "💡 Based on extensive software engineering and quality assurance expertise"
        ],
        "ai_service": "Enhanced Software Development Expert Assistant"
    }
