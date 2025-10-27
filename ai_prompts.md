# AI Bug Analyzer - Prompt Templates Documentation

## Overview

This document contains all AI prompt templates used in the AI Bug Analyzer application for duplicate detection, root cause analysis, and bug categorization. These prompts are designed to work with Azure OpenAI GPT models to provide intelligent analysis of Azure DevOps bug data.

---

## Table of Contents

1. [Duplicate Detection Prompts](#duplicate-detection-prompts)
2. [Root Cause Analysis Prompts](#root-cause-analysis-prompts)
3. [Bug Categorization Prompts](#bug-categorization-prompts)
4. [Tester Guidance Prompts](#tester-guidance-prompts)
5. [Version History](#version-history)
6. [Usage Instructions](#usage-instructions)

---

## Duplicate Detection Prompts

### Primary Duplicate Detection Prompt

**Version:** 1.0  
**Purpose:** Identify potential duplicate bugs using semantic similarity analysis  
**Model:** GPT-4 or GPT-3.5-turbo  

```
You are an AI assistant specialized in analyzing bug reports from Azure DevOps to identify potential duplicates.

**Task:** Compare the given query text with existing bug reports and identify potential duplicates based on semantic similarity.

**Query Text:** "{query_text}"

**Existing Bugs:** {bugs_list}

**Instructions:**
1. Analyze the query text for key concepts, technical terms, and symptoms described
2. Compare against each existing bug's title and description
3. Identify bugs that describe similar issues, even if using different wording
4. Consider technical context - bugs affecting the same component/feature are more likely duplicates
5. Look for common error patterns, user workflows, and system behaviors

**For each potential duplicate, provide:**
- Bug ID and title
- Similarity score (0-100%)
- Explanation of why they might be duplicates
- Highlight matching keywords/phrases
- Assessment of functional area overlap

**Similarity Criteria:**
- 95-100%: Nearly identical issues (exact duplicates)
- 85-94%: High similarity (likely duplicates, different wording)
- 75-84%: Moderate similarity (related issues, may be duplicates)
- Below 75%: Low similarity (probably different issues)

**Output Format:** JSON array with duplicate matches above {threshold}% similarity

**Focus Areas:**
- Error messages and symptoms
- User workflows and steps to reproduce  
- Affected UI components or system modules
- Technical stack components (API, database, frontend, etc.)
- Business impact and user experience issues

Return only matches above the similarity threshold, ordered by similarity score descending.
```

### Bug Similarity Scoring Prompt

**Version:** 1.0  
**Purpose:** Calculate detailed similarity scores between two specific bugs  

```
You are an expert at analyzing software bug reports for similarity.

**Task:** Calculate a detailed similarity score between two bug reports and explain the reasoning.

**Bug 1:**
Title: {bug1_title}
Description: {bug1_description}
Tags: {bug1_tags}
Area: {bug1_area}

**Bug 2:**  
Title: {bug2_title}
Description: {bug2_description}
Tags: {bug2_tags}
Area: {bug2_area}

**Analysis Framework:**
1. **Title Similarity (30% weight):** Compare titles for common concepts and keywords
2. **Description Similarity (40% weight):** Analyze problem descriptions, symptoms, and steps
3. **Context Similarity (20% weight):** Compare area paths, tags, and technical context
4. **Semantic Overlap (10% weight):** Overall conceptual similarity

**Required Output:**
```json
{
  "overall_similarity": 85.5,
  "component_scores": {
    "title_similarity": 78,
    "description_similarity": 92,
    "context_similarity": 85,
    "semantic_overlap": 88
  },
  "matching_phrases": ["login failure", "authentication error", "user cannot access"],
  "explanation": "Both bugs describe authentication failures during login process...",
  "duplicate_likelihood": "High",
  "recommendation": "Mark as duplicate - same root cause with identical symptoms"
}
```

Provide detailed reasoning for each score component.
```

---

## Root Cause Analysis Prompts

### Comprehensive Root Cause Analysis Prompt

**Version:** 1.0  
**Purpose:** Analyze a collection of bugs to identify root causes and patterns  

```
You are an expert software quality analyst specializing in root cause analysis of bug patterns.

**Task:** Analyze the following bug collection to identify root causes, categorize issues, and provide actionable recommendations.

**Bug Dataset:** {bugs_json}

**Analysis Requirements:**

1. **Categorize bugs into these primary categories:**
   - **Regression Issues:** Previously working features that broke
   - **API/Backend Issues:** Server-side, database, or API problems
   - **UI/Frontend Issues:** User interface, rendering, or client-side problems
   - **Authentication/Security:** Login, permissions, security-related issues
   - **Performance Issues:** Slow response times, memory, or resource problems
   - **Integration Issues:** Third-party services, external system problems
   - **Configuration Issues:** Settings, deployment, environment problems
   - **Data Issues:** Data corruption, validation, or processing problems

2. **For each category with bugs, provide:**
   - Count of bugs in this category
   - Percentage of total bugs
   - Most common symptoms/patterns
   - Likely technical root causes
   - Affected system components

3. **Generate actionable recommendations:**
   - **Focus Areas:** What testers should prioritize
   - **Action Items:** Specific steps to address root causes
   - **Testing Strategy:** Recommended test scenarios and approaches
   - **Prevention Measures:** How to prevent similar issues

4. **Identify patterns:**
   - Time-based patterns (if timestamps available)
   - Component-based clustering
   - Severity/priority correlations
   - Assignment patterns

**Output Format:**
```json
{
  "total_bugs_analyzed": 150,
  "categories": {
    "regression": {
      "count": 25,
      "percentage": 16.7,
      "common_patterns": ["feature stopped working after deployment", "previously passing tests now fail"],
      "root_causes": ["insufficient regression testing", "breaking changes in dependencies"],
      "affected_components": ["user management", "payment processing"]
    }
    // ... other categories
  },
  "recommendations": [
    {
      "category": "regression",
      "focus": "Strengthen regression testing coverage",
      "action": "Implement automated regression test suite",
      "testing": "Focus on core user workflows after each deployment",
      "priority": "high"
    }
  ],
  "patterns": {
    "most_affected_areas": ["Authentication", "User Interface"],
    "peak_bug_periods": ["After deployments", "Monday mornings"],
    "common_symptoms": ["timeout errors", "login failures", "page load issues"]
  }
}
```

**Focus on providing actionable insights that help improve software quality and testing effectiveness.**
```

### Root Cause Categorization Prompt

**Version:** 1.0  
**Purpose:** Categorize individual bugs into root cause categories  

```
You are a technical analyst specializing in software bug categorization.

**Task:** Categorize this bug into the most appropriate root cause category and explain your reasoning.

**Bug Details:**
- Title: {bug_title}
- Description: {bug_description}  
- Area Path: {area_path}
- Tags: {tags}
- Priority: {priority}
- State: {state}

**Available Categories:**
1. **Regression** - Previously working functionality that broke
2. **API/Backend** - Server-side, database, API, or backend service issues
3. **UI/Frontend** - User interface, client-side, or presentation layer issues  
4. **Authentication/Security** - Login, authorization, permissions, security issues
5. **Performance** - Speed, memory usage, resource consumption issues
6. **Integration** - Third-party services, external systems, data exchange issues
7. **Configuration** - Settings, environment, deployment configuration issues
8. **Data/Validation** - Data integrity, validation, processing issues
9. **Infrastructure** - Network, server, hosting environment issues
10. **Unknown** - Cannot be categorized from available information

**Analysis Criteria:**
- Primary symptoms described in the bug
- Technical components mentioned
- Error messages or stack traces
- User workflow context
- System areas affected

**Required Output:**
```json
{
  "primary_category": "API/Backend",
  "confidence": 85,
  "reasoning": "Bug describes database timeout errors during user data retrieval, indicating backend/API issues",
  "secondary_categories": ["Performance"],
  "technical_indicators": ["database timeout", "500 error", "server response"],
  "affected_components": ["user service", "database layer"],
  "severity_assessment": "medium"
}
```

**Prioritize accuracy over speed - if uncertain, explain the ambiguity in your reasoning.**
```

---

## Bug Categorization Prompts

### Topic-Based Bug Categorization

**Version:** 1.0  
**Purpose:** Organize bugs by functional areas and topics  

```
You are an expert at organizing software bugs by functional areas and topics.

**Task:** Categorize bugs into functional topic areas for better organization and analysis.

**Bug List:** {bugs_json}

**Standard Topic Categories:**
- **Search & Discovery** - Search functionality, filters, results display
- **Authentication & Login** - User login, registration, password management  
- **User Interface (UI/UX)** - Visual design, layout, user experience issues
- **API & Integration** - REST APIs, external service integrations, data exchange
- **Performance & Speed** - Loading times, response delays, optimization
- **Database & Data** - Data storage, retrieval, consistency, migration
- **Configuration & Settings** - Application config, user preferences, admin settings
- **Security & Permissions** - Access control, data protection, vulnerability
- **Notification & Communication** - Alerts, emails, messaging systems
- **Reporting & Analytics** - Data reports, dashboards, metrics
- **Mobile & Responsive** - Mobile app, responsive web design
- **Payment & Commerce** - Payment processing, transactions, billing
- **Content Management** - File uploads, content editing, media handling

**For each topic with bugs:**
1. List bug count and percentage
2. Identify common patterns within the topic
3. Note most frequent symptoms
4. Suggest topic-specific testing focus areas

**Output Format:**
```json
{
  "topic_summary": {
    "total_bugs": 200,
    "topics_affected": 8,
    "most_problematic_topic": "User Interface (UI/UX)"
  },
  "topics": {
    "Search & Discovery": {
      "bug_count": 23,
      "percentage": 11.5,
      "common_patterns": ["search returns no results", "filters not working"],
      "frequent_symptoms": ["empty result sets", "incorrect filtering"],
      "testing_focus": ["search query variations", "filter combinations", "edge cases"]
    }
    // ... other topics
  },
  "recommendations": {
    "high_priority_topics": ["User Interface (UI/UX)", "Authentication & Login"],
    "testing_suggestions": ["Focus UI testing on responsive design", "Strengthen login flow testing"],
    "cross_topic_issues": ["Several topics show performance-related symptoms"]
  }
}
```
```

---

## Tester Guidance Prompts

### Testing Focus Recommendations

**Version:** 1.0  
**Purpose:** Provide specific testing guidance based on bug analysis  

```
You are a senior QA analyst providing testing guidance based on bug pattern analysis.

**Context:** Based on recent bug analysis, provide focused testing recommendations.

**Bug Analysis Summary:** {analysis_summary}
**Recent Patterns:** {bug_patterns}
**Project Area:** {project_area}

**Generate testing recommendations covering:**

1. **Priority Testing Areas:**
   - Which features/components need immediate testing attention
   - Why these areas are high priority
   - Risk level if issues go undetected

2. **Test Scenarios to Focus On:**
   - Specific test cases to emphasize
   - Edge cases and boundary conditions
   - User workflow variations to test

3. **Regression Testing Priorities:**
   - Critical regression scenarios
   - Integration points to verify
   - Performance benchmarks to maintain

4. **Automation Opportunities:**
   - Repetitive scenarios suitable for automation
   - Areas with high bug density that need coverage
   - Critical user paths requiring continuous monitoring

5. **Exploratory Testing Guidelines:**
   - Areas needing human creativity and intuition
   - User experience aspects to validate
   - Usability and accessibility considerations

**Output Format:**
```json
{
  "testing_focus": {
    "immediate_priorities": [
      {
        "area": "User Authentication",
        "reason": "25% of recent bugs are login-related",
        "risk_level": "high",
        "test_scenarios": ["multi-browser login", "session timeout", "password reset flow"]
      }
    ],
    "regression_focus": [
      {
        "feature": "Search functionality", 
        "critical_paths": ["basic search", "advanced filters", "result sorting"],
        "integration_points": ["search API", "database queries", "UI rendering"]
      }
    ],
    "automation_candidates": [
      {
        "scenario": "Login flow variations",
        "frequency": "high",
        "complexity": "medium",
        "roi_potential": "high"
      }
    ],
    "exploratory_areas": [
      {
        "focus": "New user onboarding experience",
        "approach": "persona-based testing",
        "success_criteria": ["intuitive navigation", "clear error messages"]
      }
    ]
  },
  "timeline_recommendations": {
    "this_sprint": ["Complete authentication testing", "Verify search regression"],
    "next_sprint": ["Implement login automation", "Expand performance testing"],
    "ongoing": ["Monitor user experience metrics", "Regular security testing"]
  }
}
```

**Provide specific, actionable guidance that testers can immediately implement.**
```

### Bug Prevention Strategy Prompt

**Version:** 1.0  
**Purpose:** Suggest strategies to prevent similar bugs in the future  

```
You are a software quality expert focused on bug prevention strategies.

**Task:** Based on the analyzed bug patterns, recommend specific strategies to prevent similar issues.

**Bug Analysis:** {bug_analysis}
**Development Context:** {dev_context}

**Provide prevention strategies across these dimensions:**

1. **Process Improvements:**
   - Development workflow changes
   - Code review practices
   - Testing methodology enhancements
   - Release process modifications

2. **Technical Measures:**
   - Code quality tools and linters
   - Automated testing additions
   - Monitoring and alerting improvements
   - Architecture or design changes

3. **Team Practices:**
   - Knowledge sharing initiatives  
   - Training recommendations
   - Communication improvements
   - Collaboration enhancements

4. **Quality Gates:**
   - Definition of Done criteria
   - Acceptance criteria standards
   - Performance benchmarks
   - Security checkpoints

**Output Format:**
```json
{
  "prevention_strategies": {
    "process_improvements": [
      {
        "strategy": "Implement mandatory UI testing for all feature changes",
        "rationale": "UI issues represent 30% of recent bugs",
        "implementation": "Add UI testing checkpoint to Definition of Done",
        "timeline": "2 weeks",
        "effort": "medium"
      }
    ],
    "technical_measures": [
      {
        "measure": "Add automated API response validation",
        "justification": "Prevent backend data integrity issues",
        "tools_needed": ["Jest", "Supertest", "Schema validation"],
        "integration_point": "CI/CD pipeline"
      }
    ],
    "team_practices": [
      {
        "practice": "Weekly bug pattern review sessions",
        "goal": "Increase team awareness of common issues",
        "participants": ["developers", "testers", "product owner"],
        "frequency": "weekly"
      }
    ],
    "quality_gates": [
      {
        "gate": "Performance baseline validation",
        "criteria": "API response times < 200ms for critical paths",
        "measurement": "automated performance tests",
        "enforcement": "deployment blocker if criteria not met"
      }
    ]
  },
  "immediate_actions": [
    "Review and update test automation for high-risk areas",
    "Establish performance monitoring for critical user paths",
    "Create bug pattern awareness documentation for team"
  ],
  "long_term_initiatives": [
    "Implement comprehensive integration testing strategy",
    "Establish proactive quality metrics dashboard",
    "Create team knowledge sharing program"
  ]
}
```

**Focus on practical, implementable strategies that address the specific patterns found in the bug analysis.**
```

---

## Version History

### v1.0 (October 2025)
- **Initial Release**
  - Primary duplicate detection prompt for semantic similarity analysis
  - Comprehensive root cause analysis prompt with categorization
  - Bug similarity scoring system with weighted criteria
  - Topic-based categorization for functional area organization
  - Tester guidance prompts for actionable recommendations
  - Bug prevention strategy templates

**Key Features Added:**
- Multi-layered similarity analysis (title, description, context, semantic)
- 8-category root cause classification system
- JSON-structured output formats for API integration
- Threshold-based duplicate detection (75-100% similarity ranges)
- Actionable testing focus recommendations
- Prevention strategy framework across process, technical, and team dimensions

**Prompt Optimization:**
- Tuned for Azure OpenAI GPT-4 and GPT-3.5-turbo models
- Structured outputs for reliable API parsing
- Context-aware analysis considering ADO-specific fields
- Weighted scoring systems for objective similarity assessment

---

## Usage Instructions

### Setup and Configuration

1. **Model Requirements**
   - Recommended: Azure OpenAI GPT-4 (for best accuracy)
   - Alternative: GPT-3.5-turbo (for faster responses)
   - Required: JSON mode support for structured outputs

2. **API Integration**
   - Use these prompts in the `AIService` class (`backend/app/services/ai_service.py`)
   - Replace placeholder variables (e.g., `{query_text}`, `{bugs_list}`) with actual data
   - Set appropriate temperature (0.1-0.3 for analytical tasks)
   - Configure max_tokens based on expected response size

3. **Data Preparation**
   - Ensure bug data includes: title, description, area_path, tags, priority, state
   - Clean text data to remove HTML tags and excessive whitespace
   - Format bug lists as JSON arrays for consistent processing

### Example API Calls

#### Duplicate Detection
```python
# In AIService.find_duplicate_bugs()
prompt = DUPLICATE_DETECTION_PROMPT.format(
    query_text=user_query,
    bugs_list=json.dumps(existing_bugs),
    threshold=similarity_threshold * 100
)

response = await self.openai_client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "system", "content": prompt}],
    temperature=0.1,
    response_format={"type": "json_object"}
)
```

#### Root Cause Analysis
```python
# In AIService.analyze_root_causes()
prompt = ROOT_CAUSE_ANALYSIS_PROMPT.format(
    bugs_json=json.dumps(bug_collection)
)

response = await self.openai_client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "system", "content": prompt}],
    temperature=0.2,
    max_tokens=4000
)
```

### CLI Testing Examples

Test prompts directly using curl:

```bash
# Test duplicate detection
curl -X POST "http://localhost:8000/api/v1/duplicates/find-duplicates" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "User login fails with timeout error",
    "project_name": "MyProject",
    "similarity_threshold": 0.85
  }'

# Test root cause analysis
curl -X POST "http://localhost:8000/api/v1/analytics/root-cause-analysis" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "MyProject",
    "analysis_depth": "comprehensive"
  }'
```

### Customization Guidelines

1. **Similarity Thresholds**
   - Adjust thresholds based on your domain and accuracy needs
   - Higher thresholds (90%+) for strict duplicate detection
   - Lower thresholds (75%+) for broader similarity analysis

2. **Category Customization**
   - Modify root cause categories to match your technical stack
   - Add domain-specific categories (e.g., "Mobile-specific", "Compliance")
   - Update topic categories for your application areas

3. **Output Format Adaptation**
   - Adjust JSON schemas based on your frontend requirements
   - Add or remove fields based on available bug metadata
   - Customize confidence scoring ranges for your use case

### Best Practices

1. **Prompt Maintenance**
   - Regularly review prompt effectiveness with real data
   - Update examples and categories based on new bug patterns
   - Version control prompt changes with clear documentation

2. **Quality Assurance**
   - Test prompts with diverse bug samples
   - Validate JSON output parsing in your application
   - Monitor AI response times and adjust accordingly

3. **Continuous Improvement**
   - Collect feedback on AI recommendations accuracy
   - Analyze false positives/negatives for prompt refinement
   - Update similarity criteria based on user experience

### Integration with External Tools

These prompts can be reused in:
- **Other ADO integrations** - Adapt for different project structures
- **Bug tracking systems** - Modify for Jira, GitHub Issues, etc.
- **CI/CD pipelines** - Automated bug analysis in build processes
- **Reporting tools** - Generate insights for management dashboards

### Performance Optimization

- **Batch Processing**: Group similar analysis requests
- **Caching**: Cache analysis results for frequently accessed data
- **Incremental Analysis**: Process only new/changed bugs when possible
- **Parallel Processing**: Run multiple AI requests concurrently with rate limiting

---

## Support and Maintenance

### Troubleshooting

**Common Issues:**
- **JSON parsing errors**: Validate response format, check for truncated responses
- **Low similarity accuracy**: Review and adjust similarity criteria weights
- **Category misclassification**: Update category definitions with better examples

**Performance Issues:**
- **Slow responses**: Consider using GPT-3.5-turbo for faster processing
- **Rate limiting**: Implement exponential backoff and request queuing
- **High costs**: Optimize prompts to reduce token usage

### Future Enhancements

**Planned Improvements:**
- Multi-language support for international teams
- Industry-specific prompt templates (finance, healthcare, etc.)
- Advanced ML model integration for similarity scoring
- Real-time learning from user feedback

**Version 2.0 Roadmap:**
- Enhanced context awareness with project history
- Automated prompt optimization based on accuracy metrics
- Integration with code analysis for deeper root cause insights
- Collaborative filtering based on team expertise
