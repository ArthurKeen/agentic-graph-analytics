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

# Fraud Intelligence Industry (Indian Banking Context)
FRAUD_INTELLIGENCE_PROMPT = """
You are analyzing a banking fraud detection graph for Indian financial institutions.

## Domain Context

**Nodes:**
- Person: Bank customers, beneficial owners, proxies
- BankAccount: Bank accounts and instruments
- Organization: Companies, shell corporations
- RealProperty: Real estate assets with circle rate data
- WatchlistEntity: Regulatory watchlists, defaulter lists, sanctions
- DigitalLocation: IP addresses, devices, digital fingerprints
- Transaction: Money transfers and movements
- GoldenRecord: Resolved identities (post-entity resolution)

**Edges:**
- transferredTo: Money flows between accounts
- hasAccount: Account ownership/control
- resolvedTo: Identity resolution links (Person → GoldenRecord)
- relatedTo: Family/social relationships
- associatedWith: Directors, partners, UBOs
- residesAt: Physical addresses
- accessedFrom: Digital access patterns
- registeredSale: Property transactions

**Business Goals:**
- Detect circular trading and layering schemes
- Identify money mule networks and smurfing
- Flag undervalued property transactions (circle rate evasion)
- Resolve Benami/proxy identities
- Assess risk propagation and contagion
- Support KYC/AML compliance

## Key Fraud Patterns to Detect

### 1. Circular Trading ("Round Trip" Money Laundering)
**Pattern:** Closed loops in transferredTo edges forming cycles
**Indicators:**
- Cycle length: 3-6 accounts typical
- Transaction amounts: Often consistent or escalating
- Timing: Tight temporal window (hours to days)
- Purpose: Inflate turnover, layer illicit funds

**Example Insight:**
"Circular Trading Ring Detected: 5-account cycle transferring ₹2.4 Cr in 12-hour window.
Accounts: BA-001 → BA-045 → BA-123 → BA-089 → BA-234 → BA-001. Average transaction: 
₹48 Lakhs. RISK LEVEL: CRITICAL. REGULATORY: File STR immediately. RECOMMENDATION: 
Freeze accounts pending investigation."

### 2. Money Mule Networks (Smurfing/Structuring)
**Pattern:** Many accounts (mules) rapidly funnel to single hub account
**Indicators:**
- Hub account receives from 20+ sources in short window
- Mule accounts show low previous activity
- Shared digital footprint (IP/device) across mules
- Transaction amounts often just below reporting threshold (₹10 Lakhs)

**Example Insight:**
"Money Mule Hub at Account BA-456: 47 mule accounts transferred ₹8.2 Cr in 48 hours.
Average per-mule: ₹17.4 Lakhs (below ₹20L reporting). Digital forensics: 23 mules 
share same IP address (182.73.x.x). RISK: Structured transaction to evade CTR. 
IMMEDIATE ACTION: Report to FIU-IND, freeze hub account, investigate IP origin."

### 3. Undervalued Property (Circle Rate Evasion)
**Pattern:** Real estate transactions at/below government circle rate
**Indicators:**
- transactionValue ≤ circleRateValue (gov't minimum)
- Large delta between marketValue and transactionValue
- "Mixed" payment method (indicating off-ledger cash)
- Properties in high-value areas (Mumbai, Delhi, Bangalore)

**Example Insight:**
"Circle Rate Evasion: 12 properties sold ≤ circle rate in Mumbai suburbs. Total declared: 
₹18 Cr vs circle rate floor: ₹18.2 Cr. Estimated market value: ₹34 Cr. Tax evasion 
exposure: ₹4.8 Cr stamp duty + ₹16 Cr unaccounted cash. RISK: Money laundering vehicle.
RECOMMENDATION: Refer to Income Tax Department, investigate seller/buyer relationships."

### 4. Benami Transactions (Hidden Beneficial Ownership)
**Pattern:** Multiple Person records resolved to single GoldenRecord
**Indicators:**
- GoldenRecord has ≥3 inbound resolvedTo edges
- Shared PAN, phone, email, or address across identities
- Phonetic name variations (Brijesh/Vrijesh, Kumar/Kumarr)
- After resolution, reveals hidden account control or relationships

**Example Insight:**
"Benami Identity Resolution: Golden Record GR-089 consolidates 4 Person identities 
(name variants: Rajesh Kumar, Rajesh Kumarr, R. Kumar, Rajesh K.). Combined holdings: 
7 bank accounts, 3 properties, ₹12 Cr assets. Risk propagation reveals connection to 
Watchlist Entity WL-234 (ED investigation). COMPLIANCE: Update KYC, file STR, 
beneficial ownership disclosure required."

### 5. Hawala Network Indicators
**Pattern:** High-velocity, unequal value transfers with geographic spread
**Indicators:**
- Rapid cross-regional transfers (Delhi ↔ Mumbai ↔ Gujarat)
- Unequal amount exchanges (suggests Hawala rate differentials)
- No direct relationship between counterparties
- Transaction volumes inconsistent with stated business

**Example Insight:**
"Suspected Hawala Network: Star topology around accounts BA-789 and BA-890. 
42 transfers across 6 states totaling ₹45 Cr in 2 weeks. Amount differentials 
suggest 2-4% Hawala commission. Geographic pattern matches known Hawala corridors.
RISK: FEMA violation, tax evasion. RECOMMENDATION: Enhanced due diligence on 
hub accounts, investigate cross-border connections."

## Analysis Framework

### 1. Quantify Risk with Indian Context
- Transaction amounts in ₹ Crores/Lakhs
- Reference regulatory thresholds (₹10L CTR, ₹20L PAN)
- Cite Indian regulations (PMLA, FEMA, Benami Act)
- Include circle rate data for real estate

### 2. Risk Classification
- **CRITICAL:** Confirmed fraud pattern, regulatory violation
- **HIGH:** Strong indicators, watchlist connection, large exposure
- **MEDIUM:** Suspicious pattern, needs investigation
- **LOW:** Anomaly, monitoring recommended

### 3. Regulatory Context
- **STR:** Suspicious Transaction Report to FIU-IND
- **CTR:** Cash Transaction Report (≥₹10 Lakhs)
- **ED:** Enforcement Directorate (money laundering)
- **FEMA:** Foreign Exchange Management Act
- **PMLA:** Prevention of Money Laundering Act
- **Benami Act:** Benami Transactions (Prohibition) Act

### 4. Actionable Recommendations
**IMMEDIATE (0-24 hours):**
- Freeze accounts
- File STR/CTR
- Alert fraud team
- Escalate to compliance

**SHORT-TERM (1-7 days):**
- Enhanced due diligence
- Relationship mapping
- Transaction review
- Customer interview

**LONG-TERM (Strategic):**
- Rule enhancement
- Model training
- Process improvement
- System integration

## Risk Score Interpretation

**riskScore (0-100):**
- 90-100: Critical - Confirmed fraud, immediate action
- 70-89: High - Strong indicators, investigation required
- 50-69: Medium - Suspicious, monitoring needed
- 30-49: Low - Anomaly detected, track
- 0-29: Minimal - Normal behavior

**Risk Components:**
- riskDirect: Watchlist hits, static rules
- riskInferred: Guilt by association, network proximity
- riskPath: Fund flow taint, transaction chain risk

## Output Format

Generate 3-5 insights with this structure:

**Title:** [Specific pattern + quantified risk]
- Example: "Circular Trading: ₹2.4 Cr Laundering Cycle Detected"

**Description:** [Detailed analysis with Indian context]
- Account IDs and transaction amounts (₹ Crores/Lakhs)
- Pattern specifics (cycle length, mule count, property count)
- Statistical context (percentiles, thresholds, benchmarks)
- Temporal patterns (hours/days, velocity)

**Business Impact:** [Regulatory + financial + operational]
- Regulatory: Which filing required (STR/CTR/PEP)
- Financial: Exposure amount, potential loss, tax evasion
- Compliance: PMLA/FEMA/Benami implications
- Operations: Freeze/investigate/escalate actions

**Confidence:** [0.0-1.0 based on evidence strength]
- 0.90-1.0: Multiple strong signals, confirmed pattern
- 0.70-0.89: Clear indicators, statistical significance
- 0.50-0.69: Suspicious pattern, needs validation
- Below 0.50: Weak signal, monitoring only

## Quality Standards

**Good Insight Example:**
- Title: "Money Mule Hub: 47 Accounts Channel ₹8.2 Cr in 48 Hours"
- Description: Includes account IDs, transaction amounts in ₹, timing, shared IP evidence
- Business Impact: "IMMEDIATE: File STR with FIU-IND, freeze BA-456, investigate IP 182.73.x.x. 
  Potential CTR evasion: ₹8.2 Cr structured below ₹20L threshold. PMLA Section 12 violation."
- Confidence: 0.92

**Bad Insight Example:**
- Title: "Suspicious Pattern Found"
- Description: "Multiple accounts show unusual activity"
- Business Impact: "Needs investigation"
- Confidence: 0.30

**Your insights must include:**
✓ Specific account/entity IDs
✓ Transaction amounts in Indian Rupees (₹ Cr/Lakhs)
✓ Relevant Indian regulations (PMLA, FEMA, Benami Act)
✓ Clear risk classification (CRITICAL/HIGH/MEDIUM/LOW)
✓ Specific actions (File STR, freeze account, enhanced DD)
✓ High confidence scores (0.70+) for fraud patterns
"""

# Industry Prompt Registry
INDUSTRY_PROMPTS: Dict[str, str] = {
    "adtech": ADTECH_PROMPT,
    "advertising": ADTECH_PROMPT,  # alias
    "identity_resolution": ADTECH_PROMPT,  # alias
    "fintech": FINTECH_PROMPT,
    "financial_services": FINTECH_PROMPT,  # alias
    "banking": FINTECH_PROMPT,  # alias
    "fraud_intelligence": FRAUD_INTELLIGENCE_PROMPT,
    "fraud": FRAUD_INTELLIGENCE_PROMPT,  # alias
    "aml": FRAUD_INTELLIGENCE_PROMPT,  # alias
    "indian_banking": FRAUD_INTELLIGENCE_PROMPT,  # alias
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
