# [Project Name] - Business Requirements Template

**Project**: [Project Name]  
**Date**: [Date]  
**Department**: [Department]  
**Priority**: [Critical | High | Medium | Low]  
**Prepared by**: [Your Name/Team]

---

## Domain Description

> **💡 Why include this?** Providing explicit domain context helps the AI system generate more accurate and relevant analytics recommendations. This section should take 5-10 minutes to complete and dramatically improves the quality of generated insights.

### Industry & Business Context
[What industry are you in? What does your organization do? What's your business model?]

**Example:**
> Healthcare network for regional hospital system with 15 facilities serving 2M patients annually. Non-profit focused on care quality and coordination.

### Graph Structure Overview
[High-level description of what your graph represents - what are the nodes and edges?]

**Vertex Collections (Nodes):**
- **[Node Type 1]** ([count]): [Brief description]
- **[Node Type 2]** ([count]): [Brief description]
- **[Node Type 3]** ([count]): [Brief description]

**Edge Collections (Relationships):**
- **[Edge Type 1]** ([count]): [From] → [To] ([meaning])
- **[Edge Type 2]** ([count]): [From] → [To] ([meaning])
- **[Edge Type 3]** ([count]): [From] → [To] ([meaning])

**Scale & Activity:**
- [Key metric 1]: [value]
- [Key metric 2]: [value]
- [Key metric 3]: [value]

**Example:**
> **Nodes:**
> - **Customers** (50,000): End users making purchases
> - **Products** (200,000): Items available for sale
> - **Brands** (1,000): Sellers/manufacturers
> 
> **Edges:**
> - **Purchases** (500K/month): Customer → Product (transactions)
> - **Reviews** (100K/month): Customer → Product (feedback)
> - **Follows** (250K): Customer → Brand (subscriptions)
>
> **Scale:**
> - $5M monthly GMV
> - 50K daily active users
> - 2-year historical data available

### Domain-Specific Terminology
[Define key terms that have specific meaning in your domain]

**Format:** `Term`: Definition

**Example:**
> - **Influencer**: Customer with 100+ followers driving purchases through recommendations
> - **Conversion**: Product view → Purchase completion rate
> - **Churn**: Customer hasn't purchased in 90 days
> - **High-value Customer**: >$1,000 annual spend

### Business Context & Goals
[What are you trying to achieve? What problems are you solving? What's the strategic importance?]

**Example:**
> We're experiencing 100% YoY growth but poor retention (30% churn annually). Marketing spend is high but poorly targeted. We need to identify influential customers to focus marketing efforts and reduce acquisition costs by 40%.

### Data Characteristics
[Any unique aspects of your data? Privacy requirements? Data quality notes? Historical depth?]

**Example:**
> - 24 months of complete transactional history
> - GDPR compliant (European customers)
> - Real-time updates (hourly sync from production)
> - High data quality (98% complete profiles)
> - Customer consent tracked

---

## Executive Summary

[2-3 sentences describing what you want to accomplish with this analysis]

**Example:**
> Our e-commerce platform needs to identify influential customers and understand community structures to improve marketing ROI by 40% and increase customer lifetime value by 25%. Graph analytics will uncover hidden patterns in customer behavior and optimize our marketing spend allocation.

---

## Business Objectives

### Objective 1: [Title]
**Priority**: [Critical | High | Medium | Low]  
**Goal**: [What you want to achieve]

**Success Criteria**:
- [Measurable criterion 1]
- [Measurable criterion 2]
- [Measurable criterion 3]

**Expected Business Value**: [Quantified impact, e.g., "25% increase in revenue"]

**Timeline**: [When do you need this?]

### Objective 2: [Title]
[Repeat for each objective]

---

## Stakeholders

| Name/Role | Organization | Interests | Requirements Impact |
|-----------|--------------|-----------|---------------------|
| [Name] | [Dept] | [What they care about] | [High/Medium/Low] |
| [Name] | [Dept] | [What they care about] | [High/Medium/Low] |

**Example:**
| Name/Role | Organization | Interests | Requirements Impact |
|-----------|--------------|-----------|---------------------|
| VP Marketing | Marketing | ROI, customer targeting | High |
| Chief Data Officer | Analytics | Data quality, insights | High |
| Product Manager | Product | User experience, features | Medium |

---

## Analytical Requirements

### REQ-001: [Requirement Title]
**Type**: [Centrality | Community Detection | Path Analysis | Clustering]  
**Priority**: [Critical | High | Medium | Low]  
**Description**: [What analysis is needed]

**Business Question**: [What question does this answer?]

**Suggested Approach**: [Optional - if you have ideas, but AI will recommend]

**Expected Outputs**:
- [Output 1]
- [Output 2]
- [Output 3]

**Success Criteria**: [How will you measure success?]

### REQ-002: [Requirement Title]
[Repeat for each requirement]

---

## Constraints & Considerations

### Performance
- Analysis completion time: [timeframe]
- Graph size: [node count, edge count]
- Resource limitations: [any constraints]

### Data Quality
- Required confidence level: [percentage]
- Data completeness: [any gaps?]
- Validation approach: [how will you verify?]

### Compliance & Privacy
- Privacy regulations: [GDPR, HIPAA, etc.]
- Data anonymization: [required?]
- Audit requirements: [logging needs?]

### Budget & Timeline
- Budget: [if relevant]
- Timeline: [deadlines]
- Critical milestones: [key dates]

---

## Success Metrics

### Technical Success
- [ ] All analyses complete without errors
- [ ] Results stored and accessible
- [ ] Performance within acceptable limits
- [ ] Data quality standards met

### Business Success
- [ ] Insights are actionable
- [ ] Clear recommendations provided
- [ ] ROI estimates included
- [ ] Stakeholder acceptance achieved

### Adoption Success
- [ ] Results are understandable
- [ ] Recommendations are implementable
- [ ] Results drive decisions
- [ ] Process can be repeated

---

## Deliverables

1. **Analysis Reports**: [What reports do you need?]
2. **Insights Summary**: [Executive summary?]
3. **Action Plan**: [Recommendations?]
4. **Data Exports**: [What data outputs?]
5. **Visualizations**: [Charts, graphs?]

---

## Timeline

| Phase | Activities | Duration | Deadline |
|-------|------------|----------|----------|
| Week 1 | Schema analysis, algorithm selection | 1 week | [Date] |
| Week 2 | Execute analyses, validate results | 1 week | [Date] |
| Week 3 | Generate insights, create recommendations | 1 week | [Date] |
| Week 4 | Present findings to stakeholders | 1 week | [Date] |

---

## Notes & Additional Context

[Any other relevant information that doesn't fit above categories]

**Example:**
- This analysis will be repeated quarterly
- Results will feed into our ML recommendation engine
- Working with external consultant for domain expertise
- Integration with Salesforce CRM planned for Q2

---

## Appendices (Optional)

### Appendix A: Data Dictionary
[Define key data fields if helpful]

### Appendix B: Technical Specifications
[Any technical details about your ArangoDB setup]

### Appendix C: Related Documentation
[Links to other relevant documents]

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | [Date] | [Name] | Initial draft |
| 1.1 | [Date] | [Name] | Updated after review |

---

## 💡 Tips for Completing This Template

### Domain Description Section (Most Important!)
- **Spend 10-15 minutes here** - it dramatically improves AI recommendations
- Be specific about your business model and context
- Include approximate numbers (they don't need to be exact)
- Define domain-specific terms that might be ambiguous
- Explain what success looks like in your industry

### Business Objectives
- Make them measurable (use percentages, counts, timeframes)
- Prioritize ruthlessly (not everything can be critical)
- Link objectives to business value ($, time saved, efficiency)

### Requirements
- Focus on WHAT you want to know, not HOW to do it
- Let the AI recommend algorithms - you provide business questions
- Be specific about expected outputs

### Don't Overthink It
- The AI is smart - it can work with imperfect information
- Better to have something than nothing
- You can always refine after seeing initial results
- 80% complete is better than 100% perfect (but never started)

---

**Ready to use this template?**
1. Save a copy with your project name
2. Fill out the Domain Description first (most important!)
3. Complete Business Objectives with measurable criteria
4. List your requirements focusing on business questions
5. Run through the AI workflow and see the magic happen!

**Questions?** See `docs/getting-started/QUICK_START.md` for examples and guidance.

