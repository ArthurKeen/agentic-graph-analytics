# Supported Industry Verticals - Graph Analytics AI Platform

## Overview

The platform currently supports **5 major industry verticals** with specialized analysis prompts and pattern detectors:

---

## 1. 🎯 Ad-Tech / Identity Resolution

**Industry Keys:** `adtech`, `advertising`, `identity_resolution`

### Domain Focus:
- Advertising technology and identity resolution graphs
- Device/household clustering and attribution
- Fraud detection (botnets, invalid traffic)
- Cross-device attribution and targeting

### Key Entities:
- **Nodes:** Devices (TVs, phones, tablets), IP addresses, Apps/Sites, Households (PHIDs)
- **Edges:** Same household connections, viewing behavior, ad delivery paths

### Business Use Cases:
- Accurate household clustering (3-18 devices per household)
- Fraud detection (botnet signatures, proxy networks)
- Cross-device attribution (CTV → Mobile → Conversion)
- Audience segmentation and lookalike modeling
- Inventory forecasting

### Pattern Detection:
- **Botnet signatures:** >20 devices with >10 IPs, temporal concentration
- **Over-aggregation:** Mega-clusters (>40% of nodes), public IP false positives
- **Fragmentation:** Singleton households indicating poor resolution
- **Bridge nodes:** Devices connecting multiple households

### Metrics:
- Household cluster quality (size distribution)
- IP cardinality (devices per IP)
- Geographic clustering
- Cross-device coverage
- Revenue impact estimation

---

## 2. 💰 FinTech / Financial Services

**Industry Keys:** `fintech`, `financial_services`, `banking`

### Domain Focus:
- Financial services, payments, and banking analytics
- Transaction network analysis
- Risk assessment and compliance
- Payment flow optimization

### Key Entities:
- **Nodes:** Accounts, Users, Merchants, Financial Institutions
- **Edges:** Transactions, Transfers, Relationships

### Business Use Cases:
- Transaction pattern analysis
- Payment flow optimization
- Risk concentration detection
- Merchant network analysis
- User segmentation
- Fraud risk assessment

### Pattern Detection:
- **Concentration risk:** Small number of accounts handling large volumes
- **Network hubs:** Central accounts in payment flows
- **Suspicious patterns:** Unusual transaction velocities, circular flows
- **Segmentation:** High-value vs. low-value account clusters

### Metrics:
- Transaction volume and velocity
- Network centrality
- Risk concentration
- Payment success rates
- Customer lifetime value indicators

---

## 3. 🚨 Fraud Intelligence (Indian Banking)

**Industry Keys:** `fraud_intelligence`, `fraud`, `aml`, `indian_banking`

### Domain Focus:
- Banking fraud detection and anti-money laundering (AML)
- Specifically tuned for Indian banking regulations and context
- Entity resolution and beneficial ownership discovery
- Regulatory compliance (PMLA, FEMA, Benami Act)

### Key Entities:
- **Nodes:** Person, BankAccount, Organization, RealProperty, WatchlistEntity, DigitalLocation, Transaction, GoldenRecord
- **Edges:** transferredTo, hasAccount, resolvedTo, relatedTo, associatedWith, residesAt, accessedFrom, registeredSale

### Business Use Cases:
- Circular trading detection (round-trip money laundering)
- Money mule network identification (smurfing/structuring)
- Circle rate evasion (undervalued property transactions)
- Benami transaction detection (hidden beneficial ownership)
- Hawala network indicators
- Risk propagation and contagion analysis
- KYC/AML compliance

### Pattern Detection:
- **Circular Trading:** 3-6 account cycles, tight temporal windows
- **Money Mule Networks:** Hub accounts receiving from 20+ mules, shared IP/device
- **Circle Rate Evasion:** Transaction value ≤ government circle rate
- **Benami Clusters:** Multiple identities resolved to single beneficial owner
- **Hawala Indicators:** Cross-regional transfers with amount differentials

### Metrics & Terminology:
- **Currency:** ₹ Crores and Lakhs (Indian Rupees)
- **Regulations:** PMLA, FEMA, Benami Act, FIU-IND, CTR, STR, PEP
- **Thresholds:** ₹10L CTR, ₹20L PAN requirements
- **Risk Levels:** CRITICAL / HIGH / MEDIUM / LOW
- **Actions:** STR filing, account freeze, enhanced due diligence

### Unique Features:
- Indian banking regulatory context
- STR-ready recommendations
- Confidence scores optimized for regulatory actions (≥0.70)
- Entity resolution with Benami pattern detection

---

## 4. 👥 Social Networks

**Industry Keys:** `social`, `social_network`, `community`

### Domain Focus:
- Social network analysis
- Community dynamics and influence
- Engagement optimization
- Platform integrity

### Key Entities:
- **Nodes:** Users, Posts, Groups, Pages
- **Edges:** Connections (followers, friends), Interactions (likes, shares, comments)

### Business Use Cases:
- Community detection (organic interest groups)
- Influence analysis (key opinion leaders)
- Content distribution optimization
- Coordinated inauthentic behavior detection
- Engagement pattern analysis

### Pattern Detection:
- **Community Structure:** Modularity scores, size distribution, bridge nodes
- **Influence Patterns:** PageRank/centrality, reach and engagement rates
- **Anomalies:** Bot networks, echo chambers, viral spread patterns
- **Coordinated Behavior:** Synchronized activity, fake engagement

### Metrics:
- Community modularity
- Influence centrality
- Engagement rates
- Network position
- Viral coefficient

---

## 5. 🔧 Generic / Default

**Industry Keys:** `generic`, `default`

### Domain Focus:
- General-purpose graph analysis
- No industry-specific assumptions
- Flexible for any domain

### Use Cases:
- Exploratory data analysis
- Custom/unknown domains
- General network analysis
- Fallback for unspecified industries

### Analysis:
- Standard graph metrics
- Component analysis
- Centrality measures
- Pattern detection without domain context

---

## Industry Registry Summary

| Vertical | Primary Key | Aliases | Status |
|----------|-------------|---------|--------|
| **Ad-Tech** | `adtech` | `advertising`, `identity_resolution` | ✅ Production |
| **FinTech** | `fintech` | `financial_services`, `banking` | ✅ Production |
| **Fraud Intelligence** | `fraud_intelligence` | `fraud`, `aml`, `indian_banking` | ✅ Production |
| **Social Networks** | `social` | `social_network`, `community` | ✅ Production |
| **Generic** | `generic` | `default` | ✅ Production |

---

## Usage

### Python API

```python
from graph_analytics_ai.ai.agents import AgenticWorkflowRunner

# Ad-Tech analysis
runner = AgenticWorkflowRunner(
    graph_name="my_adtech_graph",
    industry="adtech"  # or "advertising", "identity_resolution"
)

# FinTech analysis
runner = AgenticWorkflowRunner(
    graph_name="my_payment_graph",
    industry="fintech"  # or "financial_services", "banking"
)

# Fraud Intelligence (Indian Banking)
runner = AgenticWorkflowRunner(
    graph_name="fraud_intelligence_graph",
    industry="fraud_intelligence"  # or "fraud", "aml", "indian_banking"
)

# Social Network analysis
runner = AgenticWorkflowRunner(
    graph_name="social_graph",
    industry="social"  # or "social_network", "community"
)

# Generic analysis
runner = AgenticWorkflowRunner(
    graph_name="my_graph",
    industry="generic"  # or "default"
)
```

### Checking Supported Industries

```python
from graph_analytics_ai.ai.reporting.prompts import list_supported_industries

print(list_supported_industries())
# Output: ['adtech', 'advertising', 'aml', 'banking', 'community', 
#          'default', 'financial_services', 'fintech', 'fraud', 
#          'fraud_intelligence', 'generic', 'identity_resolution', 
#          'indian_banking', 'social', 'social_network']
```

---

## Pattern Detectors by Industry

### WCC (Weakly Connected Components)

| Industry | Patterns Detected |
|----------|-------------------|
| **AdTech** | Botnets, Over-aggregation, Fragmentation, Bridge analysis |
| **Fraud Intelligence** | Money mule networks, Benami clusters, Isolated actors |
| **Generic** | Standard component analysis |

### PageRank

| Industry | Patterns Detected |
|----------|-------------------|
| **AdTech** | Over-leveraged IPs, Mega-households, Singleton analysis |
| **Fraud Intelligence** | Transaction hubs, Concentration risk, Normal distribution |
| **Generic** | Standard centrality analysis |

### Cycle Detection

| Industry | Patterns Detected |
|----------|-------------------|
| **Fraud Intelligence** | Circular trading (round-trip money laundering) |
| **Generic** | Standard cycle detection |

---

## Adding New Industries

There are **two ways** to add support for a new industry:

### Option A (recommended): **No-code Custom Vertical Generation**

You can generate a custom vertical **in your client project** without modifying this repo:

1. Generate a vertical JSON from your business requirements:

```bash
cd /path/to/your-client-project
python -m graph_analytics_ai.cli.generate_vertical \
  --input docs/business_requirements.md \
  --graph-name your_graph_name \
  --validate \
  --interactive
```

This writes: `.graph-analytics/industry_vertical.json`

2. Run the agentic workflow with either:
   - `industry="auto"` (auto-detect + generate if missing), or
   - `industry="<your_industry_key>"` (loads `.graph-analytics/industry_vertical.json` when present)

See `docs/guides/CUSTOM_VERTICALS_QUICKSTART.md` for the full walkthrough.

### Option B: Add a **built-in** vertical (platform code change)

If you want the new vertical to be shipped as a built-in platform vertical:

1. **Add an industry prompt** in `graph_analytics_ai/ai/reporting/prompts.py`
2. **Register the key/aliases** in the prompt registry
3. **Add/extend pattern detectors** in `graph_analytics_ai/ai/reporting/algorithm_insights.py`
4. **Update pattern registry** mappings

---

## Key Differentiators by Industry

### Currency & Units
- **AdTech:** USD, impressions, devices
- **FinTech:** USD/EUR/etc., transaction volume
- **Fraud Intelligence:** ₹ Crores/Lakhs (Indian Rupees)
- **Social:** Engagement counts, followers
- **Generic:** No specific units

### Regulatory Context
- **AdTech:** Privacy (GDPR, CCPA), measurement standards
- **FinTech:** PCI-DSS, financial regulations
- **Fraud Intelligence:** PMLA, FEMA, Benami Act, FIU-IND
- **Social:** Content moderation, platform policies
- **Generic:** None

### Risk Classification
- **AdTech:** Fraud risk, data quality
- **FinTech:** Transaction risk, compliance
- **Fraud Intelligence:** CRITICAL/HIGH/MEDIUM/LOW with confidence scores
- **Social:** Content integrity, bot detection
- **Generic:** General anomalies

### Action Orientation
- **AdTech:** Block traffic, adjust clustering
- **FinTech:** Flag transactions, update risk models
- **Fraud Intelligence:** File STR, freeze accounts, enhanced DD
- **Social:** Remove content, suspend accounts
- **Generic:** Investigate further

---

## Roadmap

Potential future verticals:

- **Healthcare:** Patient networks, referral patterns, outbreak tracking
- **Supply Chain:** Logistics networks, supplier relationships, risk propagation
- **Cybersecurity:** Attack graphs, threat networks, vulnerability chains
- **E-Commerce:** Product recommendations, customer segmentation, fraud detection
- **Telecommunications:** Network optimization, churn analysis, service quality
- **Real Estate:** Property networks, ownership chains, market analysis

---

**Last Updated:** February 11, 2026

**Total Supported Industries:** 5 primary verticals, 15+ keyword aliases
