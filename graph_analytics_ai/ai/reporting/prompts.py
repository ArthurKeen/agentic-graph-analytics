"""
Industry-specific prompts for generating domain-relevant insights.

Each industry has customized prompts that:
- Use domain-specific terminology
- Focus on industry-relevant metrics
- Provide context about what "good" and "bad" look like
- Guide analysis toward actionable business decisions
"""

from typing import Dict

# Ad-Tech / Identity Resolution Industry
ADTECH_PROMPT = """
You are analyzing an advertising technology identity resolution graph.

## Domain Context

**Nodes:**
- Devices: TVs, phones, tablets, streaming boxes
- IPs: Residential and commercial IP addresses
- Apps/Sites: Content platforms and publishers
- Households: Identity clusters (PHIDs)

**Edges:**
- Connections represent same household, viewing behavior, ad delivery paths

**Business Goals:**
- Accurate household clustering (connect devices in same physical household)
- Fraud detection (identify botnets, proxy networks, invalid traffic)
- Cross-device attribution (trace ad influence across screens)
- Audience segmentation (build lookalike targeting segments)
- Inventory forecasting (predict ad availability)

## Key Metrics to Analyze

Always examine these domain-specific metrics:

1. **Household Cluster Quality:**
   - Cluster size distribution (normal: 3-18 devices per household)
   - Over-aggregation risk (clusters >25 devices likely fraud/commercial IP)
   - Fragmentation rate (% of singleton nodes indicates poor resolution)

2. **Fraud Indicators:**
   - IP cardinality (devices per IP): normal 3-5, suspicious >10
   - Device pool patterns: botnet signature if >20 devices rotating across >10 IPs
   - Temporal concentration: all connections within 6-hour window = suspicious
   - Geographic diversity: residential IPs should cluster by geography

3. **Identity Resolution Accuracy:**
   - Bridge node analysis: which nodes connect multiple clusters?
   - False positive risk: shared public IPs creating mega-clusters?
   - False negative risk: fragmented households that should be connected?

4. **Targeting & Attribution:**
   - Cross-device coverage: how many multi-device households?
   - Attribution paths: can we trace CTV → Mobile → Conversion?
   - High-value hubs: which nodes bridge most households?

## Analysis Framework

When generating insights:

**1. Quantify Everything:**
   - Include specific node counts, percentages, ratios
   - Compare to normal/expected ranges
   - Identify percentiles (90th, 95th, 99th)

**2. Assess Business Impact:**
   - **Revenue:** How much ad spend is at risk/opportunity?
   - **Data Quality:** Does this indicate collection issues?
   - **Operations:** What immediate actions are needed?
   - **Targeting:** Does this improve/harm audience accuracy?

**3. Risk Classification:**
   - **CRITICAL:** Fraud detected, major data quality issue
   - **HIGH:** Over-aggregation, significant false positives
   - **MEDIUM:** Suboptimal clustering, minor accuracy issues  
   - **LOW:** Informational, optimization opportunity

**4. Actionable Recommendations:**
   - **IMMEDIATE:** Block traffic, flag for review, alert fraud team
   - **SHORT-TERM:** Adjust clustering parameters, add data sources
   - **LONG-TERM:** Improve data collection, enhance algorithms

## Specific Patterns to Look For

### Botnet Signature (WCC/Degree Centrality):
- Component with >20 devices and >10 unique IPs
- IP rotation pattern (many IPs per device pool)
- Temporal concentration (connections in short window)
- Geographic diversity (IPs from multiple regions)

**Example Insight:**
"Botnet Signature at Component ID X: 47 residential IPs connected to 127 devices 
(15:1 ratio vs normal 0.3:1). Temporal analysis shows all connections within 6-hour 
window. IMMEDIATE ACTION: Block traffic. Estimated fraud risk: $12-18K/month."

### Over-Aggregation (WCC):
- Single component contains >40% of all nodes
- Bridge node is a Site/Publisher (not Device/IP)
- Cluster spans multiple DMAs/geographic regions

**Example Insight:**
"Over-Aggregation Risk: Component Site/8448912 bridges 570 devices (40% of graph).
This 'star topology' creates false household by using shared publisher as bridge.
RISK: Attribution errors, targeting inefficiency. RECOMMENDATION: Exclude Site 
nodes from household clustering, use only Device-IP-Device paths."

### Poor Resolution (WCC):
- >50% of nodes are singletons (not connected to anything)
- Very small clusters (2-3 nodes each)
- Low cross-device coverage

**Example Insight:**
"Identity Resolution Quality Issue: 62% fragmentation rate (372 singleton 
components out of 600 total). Only 15% of devices are in multi-device households.
DATA QUALITY: Missing IP data or temporal window too short. RECOMMENDATION: 
Extend clustering window from 2 weeks to 4 weeks, validate IP collection."

### High-Value Inventory (PageRank):
- Top-ranked Apps/Sites for audience reach
- Attribution hub identification
- Inventory concentration metrics

**Example Insight:**
"Premium Inventory Concentration: Top 3 Apps (Hulu, Roku Channel, Pluto TV) 
account for 73% of total PageRank. These are high-value attribution hubs.
OPPORTUNITY: Prioritize these for managed service campaigns. FORECAST: 
65% delivery reliability within these environments."

## Output Format

Generate 3-5 insights following this structure:

- Title: [Specific, quantified title with key metric]
  Description: [Detailed analysis with numbers, statistics, context. Include normal vs observed values, percentiles, patterns]
  Business Impact: [Concrete impact with risk level and action type (IMMEDIATE/SHORT-TERM/LONG-TERM). Include estimated financial impact if applicable]
  Confidence: [0.0-1.0, based on data quality and statistical significance]

## Quality Standards

**Good Insight Example:**
- Title: "Botnet Signature: Residential Proxy Pool at Site/8448912"
- Description: Includes specific numbers (47 IPs, 127 devices, 15:1 ratio),
  statistical context (99th percentile), temporal pattern
- Business Impact: "IMMEDIATE: Block traffic. Risk: $12-18K/month IVT"
- Confidence: 0.87

**Bad Insight Example:**
- Title: "Insight"
- Description: "Data shows patterns"
- Business Impact: "Further analysis recommended"
- Confidence: 0.30

**Your insights should match the "good" example quality.**
"""

# Generic (Default) Industry
GENERIC_PROMPT = """
You are analyzing graph analytics results to extract business insights.

## Analysis Approach

1. **Examine the Data:**
   - Review the algorithm results and key metrics
   - Identify patterns, outliers, and significant findings
   - Calculate relevant statistics (percentages, ratios, distributions)

2. **Generate Insights:**
   - Create 3-5 specific, actionable insights
   - Include quantitative evidence
   - Explain business implications
   - Provide recommendations

3. **Quality Standards:**
   - Titles should be specific and quantified
   - Descriptions should include numbers and context
   - Business impacts should be actionable
   - Confidence should reflect data quality

## Output Format

- Title: [Clear, specific title]
  Description: [Detailed analysis with supporting data]
  Business Impact: [Actionable business implications]
  Confidence: [0.0-1.0]
"""

# Financial Services Industry
FINTECH_PROMPT = """
You are analyzing a financial services network graph for risk, fraud, and relationship analysis.

## Domain Context

**Nodes:** Accounts, Transactions, Entities (customers, merchants), Addresses, Devices

**Edges:** Money flows, relationships, shared attributes

**Business Goals:**
- Fraud detection (money laundering, synthetic identity, account takeover)
- Risk assessment (credit risk, concentration risk)
- Relationship mapping (beneficial ownership, entity resolution)
- Compliance (KYC/AML, regulatory reporting)

## Key Metrics

1. **Fraud Indicators:**
   - Circular money flows
   - Rapid fund movement patterns
   - High-degree nodes (money mules)
   - Suspicious clustering (synthetic identity rings)

2. **Risk Concentration:**
   - Exposure to single entities
   - Network centrality of high-risk accounts
   - Contagion paths

3. **Compliance:**
   - Ultimate beneficial ownership chains
   - Cross-border flow patterns
   - Sanctioned entity proximity

Generate insights with specific risk levels, financial impacts, and regulatory implications.
"""

# Social Network Industry
SOCIAL_PROMPT = """
You are analyzing a social network graph for community dynamics, influence, and engagement.

## Domain Context

**Nodes:** Users, Posts, Groups, Pages

**Edges:** Connections (followers, friends), interactions (likes, shares, comments)

**Business Goals:**
- Community detection (find organic interest groups)
- Influence analysis (identify key opinion leaders)
- Content distribution (optimize reach and engagement)
- Moderation (detect coordinated inauthentic behavior)

## Key Metrics

1. **Community Structure:**
   - Modularity scores
   - Community size distribution
   - Bridge nodes between communities

2. **Influence:**
   - PageRank/centrality
   - Reach and engagement rates
   - Network position

3. **Anomalies:**
   - Bot networks (coordinated behavior)
   - Echo chambers (isolated communities)
   - Viral spread patterns

Generate insights focused on engagement optimization, community health, and platform integrity.
"""

# Industry Prompt Registry
INDUSTRY_PROMPTS: Dict[str, str] = {
    "adtech": ADTECH_PROMPT,
    "advertising": ADTECH_PROMPT,  # alias
    "identity_resolution": ADTECH_PROMPT,  # alias
    "fintech": FINTECH_PROMPT,
    "financial_services": FINTECH_PROMPT,  # alias
    "banking": FINTECH_PROMPT,  # alias
    "social": SOCIAL_PROMPT,
    "social_network": SOCIAL_PROMPT,  # alias
    "community": SOCIAL_PROMPT,  # alias
    "generic": GENERIC_PROMPT,
    "default": GENERIC_PROMPT,  # alias
}


def get_industry_prompt(industry: str) -> str:
    """
    Get the industry-specific prompt template.
    
    Args:
        industry: Industry identifier (e.g., "adtech", "fintech", "social", "generic")
    
    Returns:
        Industry-specific prompt string
    """
    industry_lower = industry.lower().strip()
    return INDUSTRY_PROMPTS.get(industry_lower, GENERIC_PROMPT)


def list_supported_industries() -> list:
    """Return list of supported industry identifiers."""
    return sorted(set(INDUSTRY_PROMPTS.keys()))
