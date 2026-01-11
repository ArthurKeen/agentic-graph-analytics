# Quick Reference: Code Changes for Agent Quality Improvement

**Implementation Guide for Phase 1 (Critical Fixes)**

---

## Change 1: Fix Insight Parsing (CRITICAL)

**File**: `graph_analytics_ai/ai/reporting/generator.py`  
**Lines**: Replace lines 729-745  
**Effort**: 4 hours  
**Impact**: 🔥🔥🔥 Critical

### Current Code (BROKEN)
```python
def _parse_llm_insights(self, llm_response: str) -> List[Insight]:
    """Parse LLM response into insight objects."""
    # Simple parsing - could be enhanced
    insights = []

    # For now, create one insight from the response
    insights.append(
        Insight(
            title="LLM Analysis",
            description=llm_response[:500],  # Truncate if too long
            insight_type=InsightType.KEY_FINDING,
            confidence=0.85,
            business_impact="Derived from AI analysis of results",
        )
    )

    return insights
```

### New Code (FIXED)
```python
import re

def _parse_llm_insights(self, llm_response: str) -> List[Insight]:
    """
    Parse LLM response into insight objects.
    
    Expected format from LLM:
    - Title: [title]
      Description: [description]
      Business Impact: [impact]
      Confidence: [0.0-1.0]
    
    Returns:
        List of parsed Insight objects
    """
    insights = []
    
    # Split response into individual insights
    lines = llm_response.strip().split('\n')
    
    current_insight = {}
    current_field = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Match "- Title:" or "Title:" or "1. Title:"
        if re.match(r'^[-\d.]*\s*Title:', line, re.IGNORECASE):
            # Save previous insight if exists
            if current_insight and 'title' in current_insight:
                insights.append(self._create_insight_from_dict(current_insight))
            current_insight = {
                'title': re.sub(r'^[-\d.]*\s*Title:\s*', '', line, flags=re.IGNORECASE)
            }
            current_field = 'title'
            
        elif re.match(r'^\s*Description:', line, re.IGNORECASE):
            current_insight['description'] = re.sub(
                r'^\s*Description:\s*', '', line, flags=re.IGNORECASE
            )
            current_field = 'description'
            
        elif re.match(r'^\s*Business Impact:', line, re.IGNORECASE):
            current_insight['business_impact'] = re.sub(
                r'^\s*Business Impact:\s*', '', line, flags=re.IGNORECASE
            )
            current_field = 'business_impact'
            
        elif re.match(r'^\s*Confidence:', line, re.IGNORECASE):
            conf_str = re.sub(r'^\s*Confidence:\s*', '', line, flags=re.IGNORECASE)
            try:
                # Handle both "0.95" and "95%" formats
                conf_str = conf_str.replace('%', '').strip()
                conf_val = float(conf_str)
                if conf_val > 1.0:  # Assume percentage
                    conf_val = conf_val / 100.0
                current_insight['confidence'] = conf_val
            except (ValueError, AttributeError):
                current_insight['confidence'] = 0.7
            current_field = 'confidence'
            
        elif line and current_field and not line.startswith(('Title:', 'Description:', 'Business Impact:', 'Confidence:', '-')):
            # Continuation of current field
            if current_field in current_insight:
                current_insight[current_field] += ' ' + line
            else:
                current_insight[current_field] = line
    
    # Don't forget last insight
    if current_insight and 'title' in current_insight:
        insights.append(self._create_insight_from_dict(current_insight))
    
    # Fallback if parsing failed - at least preserve some content
    if not insights and llm_response.strip():
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Failed to parse structured insights from LLM response, using fallback")
        
        insights.append(
            Insight(
                title="Analysis Results (Parsing Failed)",
                description=llm_response[:1000],  # Keep more than 500 chars
                insight_type=InsightType.KEY_FINDING,
                confidence=0.6,  # Lower confidence for fallback
                business_impact="Manual review recommended - parsing failed",
            )
        )
    
    return insights

def _create_insight_from_dict(self, insight_dict: Dict[str, Any]) -> Insight:
    """Create Insight object from parsed dictionary."""
    title = insight_dict.get('title', 'Insight')
    description = insight_dict.get('description', 'No description provided')
    
    # Ensure minimum description length
    if len(description) < 50:
        description += " (Note: Limited detail available)"
    
    return Insight(
        title=title,
        description=description,
        insight_type=self._infer_insight_type(title, description),
        confidence=insight_dict.get('confidence', 0.7),
        business_impact=insight_dict.get('business_impact', 'Further analysis recommended'),
    )

def _infer_insight_type(self, title: str, description: str = "") -> InsightType:
    """Infer insight type from title and description."""
    combined = (title + " " + description).lower()
    
    if any(word in combined for word in ['anomaly', 'unusual', 'unexpected', 'outlier', 'spike']):
        return InsightType.ANOMALY
    elif any(word in combined for word in ['pattern', 'trend', 'distribution', 'consistent']):
        return InsightType.PATTERN
    elif any(word in combined for word in ['opportunity', 'potential', 'could', 'growth']):
        return InsightType.OPPORTUNITY
    elif any(word in combined for word in ['concern', 'risk', 'problem', 'issue', 'warning']):
        return InsightType.CONCERN
    else:
        return InsightType.KEY_FINDING
```

**Testing**:
```python
# Add to tests/unit/test_report_generator.py
def test_parse_multiple_insights():
    """Test parsing multiple insights from LLM response."""
    llm_response = """
- Title: Top 5 Nodes Control 82% of Network Influence
  Description: Analysis reveals extreme concentration. The top 5 products account for 82% of cumulative PageRank score.
  Business Impact: Focus marketing efforts on these 5 critical nodes.
  Confidence: 0.95

- Title: Network Fragmented into 3 Major Clusters
  Description: WCC analysis reveals 3 large connected clusters with 127 isolated singletons.
  Business Impact: Investigate why clusters are disconnected to improve collaboration.
  Confidence: 0.88
"""
    
    generator = ReportGenerator()
    insights = generator._parse_llm_insights(llm_response)
    
    assert len(insights) == 2
    assert "82%" in insights[0].title
    assert insights[0].confidence == 0.95
    assert "Fragmented" in insights[1].title
    assert insights[1].confidence == 0.88
```

---

## Change 2: Enable LLM Interpretation

**File**: `graph_analytics_ai/ai/agents/specialized.py`  
**Line**: 897  
**Effort**: 1 hour  
**Impact**: 🔥🔥🔥 Critical

### Current Code
```python
def __init__(
    self, llm_provider: LLMProvider, trace_collector: Optional[Any] = None
):
    super().__init__(
        agent_type=AgentType.REPORTING,
        name=AgentNames.REPORTING_SPECIALIST,
        llm_provider=llm_provider,
        system_prompt=self.SYSTEM_PROMPT,
        trace_collector=trace_collector,
    )
    self.generator = ReportGenerator(llm_provider, use_llm_interpretation=False)
```

### New Code
```python
import os

def __init__(
    self, llm_provider: LLMProvider, trace_collector: Optional[Any] = None
):
    super().__init__(
        agent_type=AgentType.REPORTING,
        name=AgentNames.REPORTING_SPECIALIST,
        llm_provider=llm_provider,
        system_prompt=self.SYSTEM_PROMPT,
        trace_collector=trace_collector,
    )
    
    # Make LLM interpretation configurable via environment variable
    use_llm = os.getenv('GAE_PLATFORM_USE_LLM_REPORTING', 'true').lower() == 'true'
    
    self.generator = ReportGenerator(
        llm_provider, 
        use_llm_interpretation=use_llm
    )
    
    if not use_llm:
        self.log("LLM interpretation disabled - using heuristic insights", "warning")
```

**Configuration** (add to `.env`):
```bash
# Enable LLM-powered report generation (default: true)
GAE_PLATFORM_USE_LLM_REPORTING=true
```

---

## Change 3: Improve Validation

**File**: `graph_analytics_ai/ai/reporting/generator.py`  
**Lines**: Replace lines 314-373  
**Effort**: 3 hours  
**Impact**: 🔥🔥 High

### Enhanced Validation Code
```python
def _validate_insights(self, insights: List[Insight]) -> List[Insight]:
    """
    Validate insight quality and filter low-quality insights.
    
    Quality criteria:
    - Confidence >= 0.5 (increased from 0.2)
    - Title length >= 15 characters
    - Description length >= 100 characters
    - Contains numbers/metrics (data-driven)
    - Business impact is specific (not generic)
    
    Args:
        insights: List of insights to validate
        
    Returns:
        Filtered list of high-quality insights
    """
    import logging
    import re
    
    logger = logging.getLogger(__name__)
    validated_insights = []
    
    for insight in insights:
        quality_score = 1.0
        issues = []
        
        # Check 1: Confidence threshold
        if insight.confidence < 0.5:
            issues.append(f"Low confidence ({insight.confidence:.2f})")
            quality_score *= 0.5
        
        # Check 2: Title quality
        if len(insight.title) < 15:
            issues.append(f"Title too brief ({len(insight.title)} chars)")
            quality_score *= 0.7
        
        # Check 3: Description quality
        if len(insight.description) < 100:
            issues.append(f"Description too brief ({len(insight.description)} chars)")
            quality_score *= 0.6
        
        # Check 4: Contains specific numbers/metrics
        has_numbers = bool(re.search(r'\d+\.?\d*%|\d+\.\d+|\d{2,}', insight.description))
        if not has_numbers:
            issues.append("No specific metrics/numbers in description")
            quality_score *= 0.7
        
        # Check 5: Business impact specificity
        generic_impacts = [
            'further analysis',
            'requires investigation',
            'derived from',
            'unable to derive',
            'impact unknown'
        ]
        if any(phrase in insight.business_impact.lower() for phrase in generic_impacts):
            issues.append("Generic/vague business impact")
            quality_score *= 0.8
        
        # Check 6: Title is not generic
        generic_titles = [
            'llm analysis',
            'analysis results',
            'insight',
            'finding',
        ]
        if insight.title.lower().strip() in generic_titles:
            issues.append("Generic title")
            quality_score *= 0.5
        
        # Adjust confidence based on quality checks
        original_confidence = insight.confidence
        insight.confidence *= quality_score
        
        # Minimum threshold for inclusion (raised from 0.2 to 0.4)
        if insight.confidence >= 0.4:
            validated_insights.append(insight)
            if issues:
                logger.info(
                    f"Insight quality concerns: '{insight.title[:50]}...' - "
                    f"{', '.join(issues)} "
                    f"(confidence: {original_confidence:.2f} → {insight.confidence:.2f})"
                )
        else:
            logger.warning(
                f"Filtered low-quality insight: '{insight.title[:50]}...' "
                f"(confidence: {insight.confidence:.2f}, issues: {', '.join(issues)})"
            )
    
    # If all insights filtered, keep best ones rather than returning empty
    if len(validated_insights) == 0 and len(insights) > 0:
        logger.error(
            f"All {len(insights)} insights filtered due to low quality! "
            "Keeping top 2 by original confidence to avoid empty report."
        )
        sorted_insights = sorted(insights, key=lambda x: x.confidence, reverse=True)
        validated_insights = sorted_insights[:2]
        for insight in validated_insights:
            insight.confidence *= 0.6  # Reduce confidence since they failed validation
    
    return validated_insights
```

**Testing**:
```python
# Add to tests/unit/test_report_generator.py
def test_validation_filters_generic():
    """Test validation filters out generic insights."""
    insights = [
        Insight(
            title="LLM Analysis",  # Generic title
            description="Short description",  # Too short
            confidence=0.9
        ),
        Insight(
            title="Top Node",  # Too brief
            description="Generic finding without numbers" * 10,  # No numbers
            confidence=0.8,
            business_impact="Further analysis needed"  # Generic impact
        ),
        Insight(
            title="Top 5 Products Account for 67% of Revenue",  # Good title
            description="Detailed analysis shows products P1-P5 generated $1.2M revenue (67% of Q4 total). Product P1 alone accounts for 28% with $560K in sales. This extreme concentration indicates strong product-market fit.",  # Good description
            confidence=0.92,
            business_impact="Double down on marketing for these 5 products. Ensure supply chain handles demand."  # Specific impact
        )
    ]
    
    generator = ReportGenerator()
    validated = generator._validate_insights(insights)
    
    # Should keep only the good one
    assert len(validated) == 1
    assert "67%" in validated[0].title
    assert validated[0].confidence >= 0.4
```

---

## Change 4: Enhance Agent System Prompt

**File**: `graph_analytics_ai/ai/agents/specialized.py`  
**Lines**: Replace lines 877-885  
**Effort**: 2 hours  
**Impact**: 🔥🔥 High

### Enhanced System Prompt
```python
SYSTEM_PROMPT = """You are a Business Intelligence Report Expert specializing in graph analytics.

## Your Expertise

**Graph Analytics Algorithms**:
- PageRank: Measuring influence and importance in networks
- Community Detection: Identifying clusters and segments (WCC, SCC, Label Propagation)
- Centrality: Finding critical nodes (Betweenness, Degree, Closeness)
- Pathfinding: Analyzing connectivity and flow

**Analysis Approach**:
1. **Quantify Everything**: Use specific numbers, percentages, and statistical measures
2. **Contextualize Findings**: Connect results to business objectives and domain context
3. **Actionable Recommendations**: Provide concrete, implementable next steps
4. **Evidence-Based**: Support every claim with data from the analysis results
5. **Business Language**: Write for stakeholders, not technical audiences

## Quality Standards for Insights

Each insight MUST include:
- **Specific Title**: Include numbers and concrete findings (e.g., "Top 5 Products Control 82% of Influence" not "Top Nodes Found")
- **Quantified Description**: Percentages, counts, comparisons, statistical measures (at least 150 characters)
- **Concrete Business Impact**: Specific actions or decisions this enables (not "further analysis needed")
- **Justified Confidence**: Based on data quality, sample size, and pattern clarity

## Good vs Bad Examples

**BAD Insight**:
- Title: "Most Influential Node Identified"
- Description: "The top node has the highest score."
- Business Impact: "Focus on this node"
- Confidence: 0.85

**WHY BAD**: Generic title, no numbers, vague impact, unjustified confidence

**GOOD Insight**:
- Title: "Top 5 Products Account for 67% of Network Influence"
- Description: "Analysis of 500 products shows extreme concentration. The top 5 products (1% of catalog) have cumulative PageRank of 0.67, driving two-thirds of purchase decisions. Product P123 leads with rank 0.28 (10x median)."
- Business Impact: "Focus 60% of marketing budget on these 5 products. Their performance disproportionately affects revenue. Implement backup suppliers to mitigate single-point-of-failure risk."
- Confidence: 0.92

**WHY GOOD**: Quantified title, specific numbers and comparisons, concrete actionable impact

## Analysis Patterns

**For PageRank**:
- Look for: Influence concentration, power law distributions, outliers
- Report: Top N nodes, percentages of total influence, concentration metrics
- Impact: Resource allocation, risk management, targeting strategies

**For Community Detection (WCC/SCC/Label Propagation)**:
- Look for: Number and sizes of communities, fragmentation, isolated nodes
- Report: Component counts, size distribution, connectivity patterns
- Impact: Segmentation strategies, integration opportunities, isolated entity investigation

**For Betweenness Centrality**:
- Look for: Bridge nodes, bottlenecks, critical paths
- Report: High-betweenness nodes, network dependencies, failure impact
- Impact: Risk mitigation, process optimization, backup planning

## Your Goal

Transform technical graph analysis results into actionable business intelligence that:
1. **Drives Decisions**: Insights lead to immediate actions, not just awareness
2. **Quantifies Impact**: Use numbers to show magnitude and importance
3. **Aligns with Objectives**: Connect findings to stated business goals
4. **Identifies Risks**: Highlight potential problems and dependencies
5. **Suggests Opportunities**: Point out areas for growth or improvement

Remember: Business stakeholders need insights they can act on THIS WEEK, not interesting observations to think about someday."""
```

---

## Change 5: Add Reasoning Chain (Optional but Recommended)

**File**: `graph_analytics_ai/ai/reporting/generator.py`  
**Add new method after `_generate_insights_llm`**  
**Effort**: 4 hours  
**Impact**: 🔥 Medium

### New Method
```python
def _create_insight_prompt(
    self,
    job: AnalysisJob,
    results_sample: List[Dict[str, Any]],
    context: Optional[Dict[str, Any]],
) -> str:
    """Create prompt for LLM insight generation with algorithm-specific guidance and business context."""
    
    # [EXISTING CODE FROM LINES 557-727 REMAINS THE SAME]
    # Just add reasoning instructions at the end before returning
    
    base_prompt = f"""[existing prompt content...]"""
    
    # NEW: Add reasoning instructions
    reasoning_extension = """

# Analysis Process (Show Your Reasoning)

Before providing final insights, briefly document your analytical thinking:

## Quick Analysis:
1. **Data Observations**: What patterns do I see? (concentrations, outliers, distributions)
2. **Statistical Analysis**: Key percentages, ratios, comparisons
3. **Business Context**: How does this relate to objectives and domain?
4. **Actionable Insights**: What specific decisions or actions does this enable?

[Brief reasoning - 2-3 sentences per point]

---

# Final Insights:

Now provide 3-5 insights in the standard format...
"""
    
    return base_prompt + reasoning_extension
```

---

## Testing Checklist

### Unit Tests
- [ ] Test `_parse_llm_insights` with multiple insights
- [ ] Test parsing with various formats (bullets, numbers, plain)
- [ ] Test fallback when parsing fails
- [ ] Test `_validate_insights` filters generic insights
- [ ] Test validation keeps high-quality insights
- [ ] Test confidence score adjustments

### Integration Tests
- [ ] Generate report with PageRank results
- [ ] Generate report with WCC results
- [ ] Verify multiple insights per report
- [ ] Verify insights have specific titles
- [ ] Verify descriptions include numbers
- [ ] Verify business impacts are concrete

### Manual Tests
- [ ] Run e-commerce workflow end-to-end
- [ ] Compare report quality with Cursor-generated
- [ ] Verify LLM interpretation can be disabled
- [ ] Check logging shows insight validation details
- [ ] Verify reports render correctly in HTML/Markdown

---

## Deployment Steps

1. **Create feature branch**
   ```bash
   git checkout -b feature/improve-agent-quality
   ```

2. **Make code changes**
   - Update `ai/reporting/generator.py` (parsing, validation)
   - Update `ai/agents/specialized.py` (enable LLM, enhance prompt)
   - Add unit tests
   - Add integration tests

3. **Test locally**
   ```bash
   pytest tests/unit/test_report_generator.py -v
   pytest tests/integration/test_agentic_workflow.py -v
   python run_agentic_workflow.py  # Full workflow test
   ```

4. **Add configuration**
   ```bash
   # Add to .env.example
   GAE_PLATFORM_USE_LLM_REPORTING=true
   
   # Add to README.md configuration section
   ```

5. **Update documentation**
   - Update `docs/EXECUTION_REPORTING_GUIDE.md`
   - Add examples of new report quality
   - Document configuration options

6. **Review and merge**
   ```bash
   git add -A
   git commit -m "Improve reporting agent quality: fix parsing, enable LLM, enhance validation"
   git push origin feature/improve-agent-quality
   # Create PR for review
   ```

7. **Monitor in production**
   - Track LLM usage and costs
   - Monitor report quality metrics
   - Collect user feedback
   - Check error rates and fallback usage

---

## Rollback Plan

If issues occur:

1. **Disable LLM interpretation**
   ```bash
   export GAE_PLATFORM_USE_LLM_REPORTING=false
   ```

2. **Revert to previous parsing**
   ```bash
   git revert <commit-hash>
   ```

3. **Monitor logs**
   ```bash
   grep "Filtered low-quality insight" logs/app.log
   grep "Failed to parse" logs/app.log
   ```

---

## Success Criteria

After deployment, verify:

- [ ] Reports contain 3-5 insights (not just 1)
- [ ] Insight titles are specific (not "LLM Analysis")
- [ ] Descriptions include percentages and numbers
- [ ] Business impacts are concrete and actionable
- [ ] Confidence scores vary (not all 0.85)
- [ ] Validation logs show quality checking
- [ ] LLM costs increase by ~$0.12 per workflow
- [ ] User feedback indicates quality improvement

---

**Implementation Time**: ~14 hours (2 days)  
**Expected Quality Improvement**: 75% → 88% relevance  
**Cost Increase**: +$0.12 per workflow  
**Risk Level**: Low (clear fixes with fallbacks)
