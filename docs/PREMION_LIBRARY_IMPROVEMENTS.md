# Graph Analytics AI Platform: Improvements for Premion Use Case

**Date:** 2026-01-13  
**Context:** Analysis based on Premion's generated reports and business requirements

## Executive Summary

The current library generates reports that are too generic and sparse for Premion's ad-tech use case. Reports show only 1 insight with 24-32% confidence when they should provide 4-5 actionable insights with 50-70% confidence. This document outlines specific improvements needed to support domain-specific reporting for ad-tech/identity resolution use cases.

---

## Issues Identified from Premion Reports

### Content Quality Problems

1. **Only 1 insight per report** (should be 4-5)
2. **Low confidence scores** (24-32% instead of 50-70%)
3. **Generic titles** ("Insight", "Analysis Results")
4. **Truncated or unparsed LLM output** (raw "# Insight 1" dumped into descriptions)
5. **Generic business impacts** ("Further analysis recommended")

### Template/Presentation Problems

6. **HTML looks amateurish** - generic dashboard style, not executive report style
7. **Embedded HTML-in-HTML** for Plotly charts creates clunky rendering
8. **No executive summary** or actionable recommendations section
9. **Missing domain-specific sections** (Risk Assessment, Data Quality Warnings, Top Actions)

---

## Recommended Library Improvements

### Priority 1: Domain-Specific Prompting (High Impact)

**Problem:** Current prompts are generic graph analytics, not tailored to ad-tech identity resolution.

**Solution:** Add industry-specific prompt templates.

**Implementation:**

```python
# graph_analytics_ai/ai/reporting/prompts.py (NEW FILE)

INDUSTRY_PROMPTS = {
    "adtech": """
You are analyzing an advertising technology identity resolution graph.

Domain Context:
- Nodes: Devices (TVs, phones, tablets), IPs (residential/commercial), Apps, Sites
- Edges: Connections representing same household, viewing behavior, ad delivery
- Business Goal: Accurate household clustering, fraud detection, audience segmentation

Key Metrics to Always Analyze:
- Household cluster sizes and distributions
- IP cardinality (devices per IP) for fraud detection
- Device diversity within clusters (cross-device patterns)
- Temporal stability of connections
- Outlier clusters (too large = fraud, too small = poor resolution)

When generating insights, focus on:
1. Identity Resolution Accuracy (false positives/negatives in household matching)
2. Fraud/Bot Detection (abnormal IP patterns, device pools)
3. Targeting Quality (household composition, cross-device coverage)
4. Business Impact (ad targeting improvements, cost savings, attribution)

Always include:
- Specific node/edge counts
- Statistical anomalies (percentiles, outliers)
- Actionable recommendations (not "investigate further")
- Risk assessment (what could go wrong)
""",
    "generic": "...",  # existing default prompt
}
```

**Add to ReportingAgent:**

```python
# graph_analytics_ai/ai/agents/specialized.py

class ReportingAgent:
    def __init__(self, industry: str = "generic", ...):
        self.industry = industry
        self.domain_context = INDUSTRY_PROMPTS.get(industry, INDUSTRY_PROMPTS["generic"])
        # Prepend to system prompt
        self.system_prompt = f"{self.domain_context}\n\n{SYSTEM_PROMPT}"
```

**Expected Impact:** 
- Insights become domain-specific ("Botnet signature" vs "Anomaly detected")
- Business impacts become actionable ("Block component ID X" vs "Investigate")
- Confidence increases because LLM has domain context

---

### Priority 2: Parsing Robustness (Critical Bug Fix)

**Problem:** LLM output is sometimes dumped raw into reports instead of being parsed.

**Example from Premion report:**
```
### 1. Analysis Results
Based on the PageRank analysis ...
# Insight 1 (PageRank):
- **Title: Site/8448912 Emerges as the Central Identity Hub (80% Concentration)**
  **Description**: Analysis of the top 10 nodes...
  **Confidence**: 0.94
# Insight 2 (PageRank):
- **Title: IP Addresses Outrank Device
```

**Root Cause:** `_parse_llm_insights` fails to extract structured insights, falls back to creating one generic insight with the raw text.

**Solution:** Improve parser with multiple fallback strategies.

```python
# graph_analytics_ai/ai/reporting/generator.py

def _parse_llm_insights(self, llm_response: str) -> List[Insight]:
    """Parse with multiple strategies."""
    
    # Strategy 1: Try structured format (Title/Description/Business Impact/Confidence)
    insights = self._parse_structured_format(llm_response)
    if insights:
        return insights
    
    # Strategy 2: Try numbered section format (# Insight 1, # Insight 2)
    insights = self._parse_numbered_sections(llm_response)
    if insights:
        return insights
    
    # Strategy 3: Try bullet/dash format
    insights = self._parse_bullet_format(llm_response)
    if insights:
        return insights
    
    # Strategy 4: Re-prompt the LLM to reformat
    logger.warning("Failed to parse LLM output, re-prompting for structured format")
    insights = self._reformat_and_parse(llm_response)
    if insights:
        return insights
    
    # Final fallback: Create generic insight (current behavior)
    logger.error("All parsing strategies failed, using raw output")
    return self._create_generic_insight(llm_response)

def _parse_numbered_sections(self, text: str) -> List[Insight]:
    """Parse '# Insight 1 (PageRank):' format."""
    pattern = r'# Insight \d+.*?:\s*\n\s*-\s*\*\*Title:\s*(.+?)\*\*\s*\n\s*\*\*Description\*\*:\s*(.+?)\n\s*\*\*Business Impact\*\*:\s*(.+?)\n\s*\*\*Confidence\*\*:\s*([\d.]+)'
    # ... implementation
```

**Expected Impact:**
- No more raw LLM dumps in reports
- All insights properly structured
- Higher quality presentation

---

### Priority 3: HTML Report Template Overhaul

**Problem:** Current template looks like an internal dashboard, not an executive report.

**Solution:** Create professional report templates.

**New Template Structure:**

```html
<!-- graph_analytics_ai/ai/reporting/templates/executive_report.html -->

<!DOCTYPE html>
<html>
<head>
    <style>
        /* Clean, professional styling */
        body { font-family: 'Inter', sans-serif; }
        .report-title { 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
        }
        .executive-summary { /* Prominent top section */ }
        .key-findings { /* Top 3 insights highlighted */ }
        .detailed-analysis { /* Full insights list */ }
        .action-items { /* Bulleted recommendations */ }
        .data-quality-warnings { /* Flags/caveats */ }
    </style>
</head>
<body>
    <div class="report-title">
        <h1>{{ use_case_name }}</h1>
        <div class="metadata">{{ algorithm }} | {{ date }} | {{ confidence_level }}</div>
    </div>
    
    <section class="executive-summary">
        <h2>Executive Summary</h2>
        <p>{{ auto_generated_summary }}</p>
        <div class="key-metrics">
            <!-- 3-5 critical numbers -->
        </div>
    </section>
    
    <section class="key-findings">
        <h2>Top 3 Findings</h2>
        <!-- Highlighted boxes for top insights -->
    </section>
    
    <section class="risk-assessment">
        <h2>Risk Factors</h2>
        <!-- Domain-specific risks (fraud, data quality, etc) -->
    </section>
    
    <section class="action-items">
        <h2>Recommended Actions</h2>
        <ol>
            <!-- Extracted from business impacts -->
        </ol>
    </section>
    
    <section class="visualizations">
        <h2>Supporting Data</h2>
        <!-- Clean Plotly embeds -->
    </section>
    
    <section class="detailed-analysis">
        <h2>Detailed Insights</h2>
        <!-- All insights with full context -->
    </section>
</body>
</html>
```

**Expected Impact:**
- Professional presentation suitable for stakeholders
- Clear hierarchy (summary → findings → details)
- Actionable recommendations up front

---

### Priority 4: Algorithm-Specific Insight Templates

**Problem:** Generic insights don't leverage algorithm-specific patterns.

**Solution:** Create templates for each algorithm with domain examples.

```python
# graph_analytics_ai/ai/reporting/algorithm_insights.py (NEW)

WCC_ADTECH_PATTERNS = [
    {
        "pattern": "single_dominant_cluster",
        "detection": lambda results: max(cluster_sizes) / sum(cluster_sizes) > 0.7,
        "insight_template": """
Title: Identity Graph Dominated by Single Super-Cluster ({pct}% of Nodes)
Description: Component {component_id} contains {size} nodes ({pct}% of graph). 
This indicates either:
1. Successful household resolution (good)
2. Over-aggregation due to shared public IP (risk)
3. Data quality issue with universal bridge node (critical)

Statistical Context:
- Expected max cluster size for residential IPs: 15-20 devices
- Observed: {size} devices
- Risk Level: {risk_level}

Business Impact: {recommendation}
Confidence: 0.85
"""
    },
    {
        "pattern": "fragmentation",
        "detection": lambda results: len([c for c in clusters if size == 1]) / len(clusters) > 0.5,
        "insight_template": "..."
    }
]

PAGERANK_ADTECH_PATTERNS = [
    {
        "pattern": "ip_dominance",
        "detection": lambda results: top_node_type == "IP" and score_ratio > 10,
        "insight_template": "..."
    }
]
```

**Expected Impact:**
- Insights that directly address Premion's use cases
- Statistical benchmarks included
- Clear good/bad/critical classifications

---

### Priority 5: Confidence Calibration for Ad-Tech

**Problem:** Validation is too strict for domain-specific language.

**Solution:** Industry-specific validation rules.

```python
# graph_analytics_ai/ai/reporting/config.py

@dataclass
class IndustryValidationRules:
    """Validation rules per industry."""
    min_confidence: float
    require_quantification: bool
    generic_impact_phrases: List[str]
    domain_specific_terms: List[str]  # Don't penalize these

INDUSTRY_VALIDATION = {
    "adtech": IndustryValidationRules(
        min_confidence=0.25,  # Lower than generic (0.3)
        require_quantification=False,  # Fraud patterns may be qualitative
        generic_impact_phrases=[
            "requires investigation",
            "further analysis"
        ],
        domain_specific_terms=[
            "botnet", "proxy", "residential IP", "device pool",
            "household cluster", "cross-device", "attribution",
            "inventory", "targeting", "fraud", "IVT"
        ]  # Don't penalize as "generic"
    )
}
```

**Expected Impact:**
- Ad-tech reports pass validation with higher success rate
- Domain terminology preserved
- Fewer false negatives

---

## Implementation Roadmap

### Phase 1: Critical Fixes (1-2 days)
1. ✅ Relax validation thresholds (DONE - commit c8d8fca)
2. Fix LLM parsing with fallback strategies
3. Add re-prompting on parse failure

### Phase 2: Domain Support (2-3 days)
4. Add industry prompt templates (adtech, fintech, social, generic)
5. Add industry validation rules
6. Add algorithm-specific insight patterns

### Phase 3: Presentation (2-3 days)
7. Create executive report HTML template
8. Add auto-generated executive summary
9. Add risk assessment and action items sections

### Phase 4: Testing & Documentation (1-2 days)
10. Add unit tests for new parsers
11. Add integration test with Premion-like data
12. Update documentation with industry examples

---

## Configuration for Premion (Immediate)

Until library improvements are complete, Premion should use:

```bash
# Lenient settings for ad-tech
export GAE_PLATFORM_REPORTING_MIN_CONFIDENCE=0.2
export GAE_PLATFORM_REPORTING_USE_REASONING=true
export GAE_PLATFORM_MAX_LLM_INSIGHTS_PER_REPORT=6
export GAE_PLATFORM_REQUIRE_QUANTIFICATION=false
```

---

## Testing Strategy

### Test Case 1: WCC Household Clustering
**Input:** 1000 nodes, 1 dominant cluster (570 nodes), rest fragmented  
**Expected:** 3-5 insights about:
- Over-aggregation risk for dominant cluster
- Fragmentation patterns
- Household size distribution analysis
- Data quality assessment

**Current:** 1 generic insight at 30% confidence  
**Target:** 4 insights at 45-70% confidence

### Test Case 2: PageRank Ad Inventory Ranking
**Input:** Mixed node types (IPs, Devices, Apps) with clear top-10  
**Expected:** 3-5 insights about:
- Node type distribution in top ranks
- Concentration metrics
- Inventory value recommendations
- Attribution hub identification

**Current:** Unparsed LLM dump with truncated content  
**Target:** 4 clean insights at 50-75% confidence

---

## Success Metrics

| Metric | Current (Premion Reports) | Target |
|--------|---------------------------|--------|
| Insights per report | 1 | 4-5 |
| Avg confidence | 28% | 55-70% |
| Parsing success rate | ~60% (some dumps) | 98% |
| Domain relevance | Low (generic) | High (ad-tech specific) |
| Actionability score | 2/10 | 8/10 |
| HTML presentation | 4/10 (dashboard style) | 9/10 (executive report) |

---

## Long-Term Vision: Industry Packs

Create "industry packs" that users can install:

```python
from graph_analytics_ai.industries import adtech, fintech, social

runner = AgenticWorkflowRunner(
    industry_pack=adtech.PremionPack(
        prompts=adtech.PROMPTS,
        validation=adtech.VALIDATION_RULES,
        html_template=adtech.EXECUTIVE_TEMPLATE,
        insight_patterns=adtech.ALGORITHM_PATTERNS
    )
)
```

**Benefit:** 
- Users get domain-optimized reports out of the box
- Library remains generic at core
- Community can contribute industry packs

---

## Appendix: Example "Good" Insight for Premion

```markdown
### Botnet Signature: Residential Proxy Pool at Site/8448912

**Description:**
Component Site/8448912 exhibits a classic botnet pattern with 47 unique residential 
IPs (median IP: 73.169.x.x range) connected to a pool of 127 devices within a 24-hour 
window. Normal household behavior shows 1-3 IPs per 5-15 devices. This component 
shows a 15:1 IP-to-device ratio, indicating coordinated device rotation across a 
residential proxy network.

**Statistical Evidence:**
- IP cardinality: 47 (99th percentile for households: 3)
- Device pool size: 127 (99th percentile: 18)
- Temporal pattern: All connections within 6-hour window (suspicious)
- Geographic diversity: IPs from 12 different /16 subnets

**Business Impact:**
IMMEDIATE ACTION: Block traffic from component Site/8448912 to prevent Invalid 
Traffic (IVT). This pattern matches known fraud vendor "Proxy-Rack" signature. 
Estimated monthly ad spend at risk: $12K-18K based on current bid rates.

SECONDARY: Audit upstream data source for Site node. If this is a legitimate 
publisher site, investigate why it's being used as a bridge node in the identity 
graph.

**Confidence:** 87%
```

This is what Premion reports should look like.
