# Domain Description Best Practices Guide

**Purpose:** Help users write effective domain descriptions that improve AI recommendation quality  
**Audience:** Business analysts, data scientists, product managers  
**Time to Read:** 5 minutes  
**Time to Write Your Own:** 10-15 minutes  

---

## Why Domain Descriptions Matter

### The Impact
Adding a well-written domain description to your requirements document provides:
- **15-25% improvement** in AI recommendation accuracy
- **Better algorithm matching** to your specific business needs  
- **More contextual insights** in generated reports
- **Domain-specific terminology** in outputs
- **Reduced validation warnings** (avoids 30% confidence penalty)

### How It Works
The AI system uses your domain description to:
1. **Understand context** when interpreting requirements
2. **Select appropriate algorithms** based on your domain characteristics  
3. **Generate relevant insights** using your terminology
4. **Make business-relevant recommendations**

**Without domain context:**
```
"Identify influential users" → Generic PageRank suggestion
```

**With domain context:**
```
Domain: E-commerce marketplace
"Identify influential users" → 
  - PageRank for purchase influencers
  - Community Detection for customer segments
  - Betweenness for brand connectors
  + Explanations in e-commerce terminology!
```

---

## What to Include

### 1. Industry & Business Context (Required)
**Purpose:** Establish what industry you're in and what your organization does

**What to Write:**
- Industry name (e-commerce, healthcare, finance, logistics, etc.)
- Your business model (marketplace, B2B, B2C, SaaS, etc.)
- Organizational type (enterprise, startup, non-profit, government)
- Brief description of what you do

**Good Examples:**
```markdown
✅ Healthcare network for regional hospital system with 15 facilities 
   serving 2M patients annually. Non-profit focused on care quality 
   and reducing treatment delays.

✅ B2B SaaS platform connecting enterprise buyers with software vendors. 
   Marketplace model earning commission on $50M annual contract value.

✅ Financial services company providing fraud detection for 500+ banks. 
   Real-time transaction monitoring protecting $10B daily volume.
```

**Bad Examples:**
```markdown
❌ We do healthcare stuff.
❌ Technology company.
❌ Graph database user.
```

**Why it matters:** Industry determines which algorithms are most valuable. Healthcare needs different analytics than e-commerce.

---

### 2. Graph Structure Overview (Required)
**Purpose:** Explain what your nodes and edges represent

**What to Write:**
- **Node types** with approximate counts
- **Edge types** with meanings
- **Scale metrics** (transactions/day, active users, etc.)

**Template:**
```markdown
**Nodes:**
- **[Type 1]** ([count]): [brief description]
- **[Type 2]** ([count]): [brief description]
- **[Type 3]** ([count]): [brief description]

**Edges:**
- **[Type 1]** ([count]): [From] → [To] ([meaning])
- **[Type 2]** ([count]): [From] → [To] ([meaning])

**Scale:**
- [Key metric 1]: [value]
- [Key metric 2]: [value]
```

**Good Example:**
```markdown
✅ **Nodes:**
   - **Customers** (50,000): End users making purchases
   - **Products** (200,000): Items for sale across 500 categories
   - **Sellers** (1,000): Brands and merchants

   **Edges:**
   - **Purchases** (500K/month): Customer → Product (transactions)
   - **Reviews** (100K/month): Customer → Product (ratings 1-5 stars)
   - **Follows** (250K): Customer → Seller (subscriptions)

   **Scale:**
   - $5M monthly GMV (Gross Merchandise Value)
   - 50,000 daily active users
   - 2 years historical data
```

**Bad Example:**
```markdown
❌ We have users and products.
❌ Big graph with lots of edges.
❌ Standard e-commerce data.
```

**Why it matters:** 
- Algorithm selection depends on graph structure (bipartite vs. homogeneous)
- Scale determines engine sizing and performance expectations
- Edge types indicate which algorithms make sense

---

### 3. Domain-Specific Terminology (Highly Recommended)
**Purpose:** Define terms that have specific meaning in your domain

**What to Write:**
- Key terms that might be ambiguous
- Metrics that are domain-specific
- Business concepts that need explanation

**Format:**
```markdown
- **[Term]**: [Definition in your context]
- **[Term]**: [Definition in your context]
```

**Good Examples:**
```markdown
✅ E-commerce:
   - **Influencer**: Customer with 100+ followers driving affiliate purchases
   - **Conversion**: Product view → Purchase completion rate
   - **High-Value Customer**: >$1,000 annual lifetime value
   - **Churn**: No purchase in 90 days

✅ Healthcare:
   - **Primary Care Physician (PCP)**: First point of contact for patients
   - **Referral Bottleneck**: >14 day delay from referral to appointment
   - **Network Adequacy**: % patients accessing specialist within 30 days
   - **Readmission**: Patient return within 30 days of discharge

✅ Finance:
   - **Suspicious Transaction**: Pattern matching fraud indicators
   - **Network Risk**: Exposure through connected entities
   - **Velocity**: Transaction frequency in time window
   - **Linkage**: Shared identifying attributes (address, device, etc.)
```

**Why it matters:** 
- AI uses your terminology in reports (not generic terms)
- Prevents misinterpretation of requirements
- Makes outputs immediately usable by business stakeholders

---

### 4. Business Context & Goals (Highly Recommended)
**Purpose:** Explain what you're trying to achieve and why

**What to Write:**
- Current challenges you're facing
- Strategic goals you're working toward
- Why this analysis matters to your business
- Expected business impact

**Good Examples:**
```markdown
✅ We're experiencing 100% YoY growth but customer retention is poor 
   (30% annual churn). Marketing spend is high but poorly targeted. 
   We need to identify influential customers to focus marketing efforts 
   and reduce customer acquisition costs by 40%.

✅ Hospital system facing CMS penalties for high readmission rates. 
   Need to identify referral bottlenecks causing treatment delays. 
   Goal: Reduce average referral time from 21 days to 14 days, 
   saving an estimated $5M annually in penalties and improving 
   patient outcomes.

✅ Fraud losses increased 50% YoY as fraudsters become more sophisticated. 
   Current rules-based system has 80% false positive rate. Need graph 
   analytics to detect fraud rings and reduce false positives by 60% 
   while improving fraud detection by 30%.
```

**Bad Examples:**
```markdown
❌ We want to use graph analytics.
❌ Management asked for this.
❌ Trying to improve things.
```

**Why it matters:**
- Helps AI understand which insights are most valuable
- Guides recommendation prioritization
- Influences success criteria and report focus

---

### 5. Data Characteristics (Optional but Helpful)
**Purpose:** Note any unique aspects of your data

**What to Write:**
- Historical data depth available
- Update frequency (real-time, daily, monthly)
- Data quality notes
- Privacy/compliance requirements
- Any data limitations

**Good Examples:**
```markdown
✅ - 24 months of complete transactional history
   - Real-time updates (hourly CDC from production)
   - GDPR compliant (European customers, consent tracked)
   - High data quality (98% profile completeness)
   - Known limitation: Follower relationships only tracked since Jan 2024

✅ - HIPAA-compliant (all patient data de-identified)
   - 3 years historical referral data from Epic EMR
   - Daily batch updates
   - 95% data completeness (some specialties underreported)
   - Cross-facility data consolidated via EHR integration
```

**Why it matters:**
- Affects algorithm selection (streaming vs. batch)
- Influences confidence in recommendations
- Helps set realistic expectations
- Important for compliance and audit

---

## Complete Example: E-commerce Fashion Marketplace

```markdown
## Domain Description

### Industry & Business Context
Fashion e-commerce marketplace connecting 1,000+ independent clothing 
brands with millions of style-conscious consumers. We operate a marketplace 
business model where we facilitate transactions between sellers (fashion brands) 
and buyers (end customers), earning 15% commission on each sale. We're a 
growth-stage startup ($50M ARR) competing against larger players through 
superior personalization and community features.

### Graph Structure Overview

**Nodes:**
- **Customers** (500,000): Fashion shoppers, age 18-45, primarily female (75%)
- **Products** (200,000): Clothing items (tops, bottoms, dresses, accessories)
- **Brands** (1,000): Independent designers and established fashion labels
- **Categories** (50): Product taxonomy for navigation

**Edges:**
- **Purchases** (2.5M total): Customer → Product (completed transactions)
- **Views** (50M total): Customer → Product (browsing behavior, last 90 days)
- **Reviews** (500K): Customer → Product (1-5 star ratings with text)
- **Follows** (1M): Customer → Customer (style inspiration relationships)
- **Favorites** (5M): Customer → Product (saved items, wishlist)
- **Sells** (200K): Brand → Product (product catalog)

**Scale:**
- $120M annual GMV (Gross Merchandise Value)
- 100,000 daily active users
- Average order value: $85
- 40% repeat purchase rate annually
- Peak: Black Friday (10x normal traffic)

### Domain-Specific Terminology

- **Influencer**: Customer with 100+ followers who drives >$10K in 
  attributed purchases through style inspiration
- **Fashion Trendsetter**: Influencer whose purchases are viewed within 
  48 hours by 50+ followers
- **Social Shopper**: Customer who makes 30%+ of purchases after viewing 
  an influencer's items
- **Style Community**: Group of customers with similar fashion preferences 
  (streetwear, bohemian, minimalist, etc.)
- **Conversion**: Product view → Purchase completion rate (currently 3.5%)
- **Engagement Score**: Combined metric of views, favorites, reviews 
  (used for personalization)
- **High-Value Customer**: >$1,000 annual spend or >20 transactions/year
- **Style Affinity**: Similarity score between customers based on 
  overlapping product views/purchases
- **Co-purchase Strength**: Probability two items are bought together 
  (used for bundling)
- **Churn**: No purchase in 90 days (30% of customers churn annually)

### Business Context & Goals

We're experiencing strong growth (100% YoY) but facing challenges:

**Current Problems:**
1. **Poor Retention**: 30% annual churn rate, industry average is 20%
2. **Inefficient Marketing**: $50 CAC but only 40% become repeat customers
3. **Generic Recommendations**: 3.5% conversion rate, competitors at 5%+
4. **Unknown Influencers**: Spending equally on all customers vs. focusing 
   on influential users who drive organic growth

**Strategic Goals:**
1. Identify top 1,000 fashion influencers and create VIP program
2. Reduce marketing spend by 40% while maintaining growth
3. Increase conversion rate from 3.5% to 5% through better recommendations
4. Improve retention from 70% to 85% through personalized experiences
5. Understand natural customer communities to enable targeted campaigns

**Why This Matters:**
At our growth stage, improving unit economics is critical. We hypothesize 
that a small percentage of customers (influencers) drive the majority of 
purchasing decisions through social proof. By identifying and optimizing 
for these customers, we can dramatically improve marketing ROI and create 
a self-sustaining growth flywheel.

**Success = $5M annual savings + 25% increase in organic revenue**

### Data Characteristics

- **Historical Depth**: 24 months complete transactional data, 12 months 
  social graph data
- **Update Frequency**: Real-time (streaming CDC from production database)
- **Data Quality**: 98% profile completeness, <0.1% fraud/bot accounts
- **Compliance**: GDPR compliant (EU customers), CCPA compliant (CA residents)
- **Privacy**: Customer consent tracked, opt-outs honored
- **Known Limitations**: 
  - Follower relationships only tracked since Jan 2024
  - Some brands have incomplete product metadata
  - Views only tracked for logged-in users (60% of traffic)
- **Integration**: Feeds into Segment CDP, exports to Salesforce, powers 
  recommendation engine
```

---

## Domain Description Checklist

Use this checklist when writing your domain description:

### Required Elements
- [ ] **Industry clearly stated** (healthcare, e-commerce, finance, etc.)
- [ ] **Business model described** (marketplace, B2B, SaaS, etc.)
- [ ] **Node types listed** with approximate counts
- [ ] **Edge types explained** with meanings
- [ ] **Scale metrics provided** (transactions, users, etc.)
- [ ] **Business context included** (problems, goals)

### Highly Recommended
- [ ] **Domain terms defined** (at least 3-5 key terms)
- [ ] **Quantified goals** (percentages, dollar amounts, time savings)
- [ ] **Current challenges explained**
- [ ] **Success criteria stated**

### Optional but Valuable
- [ ] **Data characteristics** noted (depth, quality, compliance)
- [ ] **Integration context** (how results will be used)
- [ ] **Timeline context** (urgent vs. exploratory)
- [ ] **Stakeholder priorities** mentioned

---

## How Long Should It Be?

### Minimum Viable (5 minutes)
- 2-3 sentences per section
- Just the basics
- Better than nothing!

**Example:**
> E-commerce marketplace. 50K users, 200K products. Purchases and reviews 
> as main relationships. Scale: $5M monthly. Goal: Find influencers to 
> reduce marketing costs.

### Recommended (10-15 minutes)
- 1-2 paragraphs per section
- Key details included
- Optimal quality/effort ratio

**Example:** See "Complete Example" above

### Comprehensive (30 minutes)
- Multiple paragraphs
- Extensive detail
- Diminishing returns

**Note:** Don't overthink it! The "Recommended" level provides 90% of the 
benefit with reasonable effort. You can always refine later.

---

## Common Mistakes to Avoid

### ❌ Too Vague
```markdown
We're a technology company with users and data.
```
**Problem:** AI can't provide relevant recommendations

### ❌ Too Technical
```markdown
Graph has 3 vertex collections and 5 edge collections using ArangoDB 3.11 
with 16GB RAM and SSD storage running on AWS EC2 t3.xlarge instances...
```
**Problem:** Technical specs aren't helpful for business insights

### ❌ Missing Context
```markdown
**Nodes:** users, products, orders
**Edges:** purchased
```
**Problem:** No business context to guide recommendations

### ❌ Generic Terms Without Definition
```markdown
We want to find influencers and communities.
```
**Problem:** "Influencer" means different things in different domains

### ✅ Just Right
```markdown
E-commerce fashion marketplace. Customers (50K) purchase from Brands (1K). 
Influencers = customers with 100+ followers who drive affiliate purchases. 
Goal: Identify top 1,000 influencers to reduce $5M marketing spend.
```
**Why:** Clear, contextual, actionable, business-focused

---

## Tips for Success

### 1. Start with "Why"
Before diving into technical details, explain WHY you're doing this analysis.

### 2. Use Your Language
Write in your domain's natural language, not "graph speak". Define terms 
that might be ambiguous.

### 3. Quantify Everything
Use numbers: percentages, dollar amounts, counts, timeframes. 
"Improve retention" → "Increase retention from 70% to 85%"

### 4. Think About Your Audience
Your description will be read by:
- The AI system (needs context for recommendations)
- Business stakeholders (need to understand outputs)
- Future you (need to remember what you wanted)

### 5. Don't Overthink It
- 80% complete is better than 100% perfect (but never started)
- You can refine after seeing initial results
- The AI is smart - it works with imperfect information

### 6. Use Examples
When defining terms or describing concepts, give examples:
```markdown
✅ **High-Value Customer**: Annual spend >$1,000 (e.g., buys 2-3 items/month, 
   average order $85, total 15-20 orders/year)

vs.

❌ **High-Value Customer**: Customers who spend a lot
```

---

## Before and After Examples

### Example 1: Healthcare

**BEFORE (Vague):**
```markdown
Healthcare organization. Want to analyze doctor referrals.
```

**AFTER (Clear):**
```markdown
Regional hospital network with 15 facilities serving 2M patients across 
5 states. 500 doctors across 30 specialties. Problem: Referral delays 
causing treatment bottlenecks (avg 21 days from referral to appointment, 
goal is <14 days). Nodes: Doctors (500), Patients (2M de-identified), 
Hospitals (15). Edges: Referrals between doctors (50K/year), patient 
visits (500K/year). Goal: Reduce referral time by 33% to avoid $5M in 
CMS penalties and improve patient outcomes.
```

### Example 2: Finance

**BEFORE (Too Technical):**
```markdown
Transaction graph for fraud detection. Using Neo4j GDS algorithms.
```

**AFTER (Business-Focused):**
```markdown
Digital payment platform processing $10B daily for 500+ financial institutions. 
Fraud losses: $50M annually, increasing 50% YoY. Nodes: Accounts (100M), 
Merchants (1M), Devices (50M). Edges: Transactions (500M/day), shared 
attributes (address, phone, device). Fraud Ring = 3+ accounts with shared 
identifiers making suspicious transactions. Goal: Detect fraud rings 30% 
faster while reducing false positives from 80% to 40%, saving $20M annually.
```

---

## FAQ

### Q: How technical should I be?
**A:** Focus on business context, not technical architecture. The AI doesn't 
need to know your database version or server specs.

### Q: What if I don't know exact numbers?
**A:** Rough estimates are fine! "~50K users" is much better than "lots of users". 
Order of magnitude is what matters (thousands vs. millions).

### Q: Should I include algorithms I want?
**A:** You CAN, but it's optional. Focus on business questions. Let the AI 
recommend algorithms. You might be surprised by what it suggests!

### Q: How specific should domain terms be?
**A:** Define anything that might be ambiguous or has special meaning in your 
domain. When in doubt, define it.

### Q: What if my domain is unique/novel?
**A:** Even better! The AI is great with novel domains. Just explain clearly 
what makes your domain special.

### Q: Can I skip this if I'm in a hurry?
**A:** You CAN, but you'll get generic recommendations. Spending 10 minutes 
here saves hours of clarification later and dramatically improves output quality.

---

## Next Steps

1. **Use the template**: See `examples/requirements_template.md`
2. **Review examples**: See `examples/use_case_document.md` 
3. **Write your domain description** (10-15 minutes)
4. **Run the workflow** and see improved recommendations!
5. **Refine if needed** based on results

---

**Remember:** The goal is to help the AI understand your business context 
well enough to make relevant recommendations. Think of it like briefing a 
smart consultant - give them enough context to be useful!

**Questions?** See `docs/getting-started/QUICK_START.md` for more guidance.

