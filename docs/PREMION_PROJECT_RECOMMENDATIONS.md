# Premion Project: How to Get Better Reports

**Date:** 2026-01-13  
**Purpose:** Immediate actions for Premion to improve report quality

---

## The Problem

Your reports are "dog shit" because:
- Only 1 insight per report (should be 4-5)
- 24-32% confidence (should be 50-70%)
- Generic titles ("Insight", "Analysis Results")  
- Unparsed LLM dumps in content
- Amateurish HTML

---

## Immediate Fix (30 Minutes)

### Step 1: Set Environment Variables

Add to your script or `.env`:

```bash
export GAE_PLATFORM_REPORTING_MIN_CONFIDENCE=0.2
export GAE_PLATFORM_REPORTING_USE_REASONING=true
export GAE_PLATFORM_MAX_LLM_INSIGHTS_PER_REPORT=6
```

### Step 2: Update Library

```bash
cd ../graph-analytics-ai-platform
git pull origin main
pip install -e .
cd ../premion-graph-analytics
```

### Step 3: Re-run

```bash
python scripts/run_household_analysis.py
```

**Expected Result:** 1→5 insights, 30%→55% confidence

---

## Root Cause: Business Requirements Too Broad

Your `business_requirements.md` is well-written but too academic. The LLM needs:

1. **Specific thresholds** (not "detect fraud" but "flag IPs with >20 devices")
2. **Example insights** showing what "good" looks like
3. **KPIs with ranges** (household size: 3-18 normal, >25 fraud)
4. **Decision criteria** (what action to take at each threshold)

### NotebookLM Prompt to Regenerate Requirements

```
Rewrite Premion business requirements for AI report generation.

Include:

1. MEASURABLE OBJECTIVES
   - "Achieve 95% household accuracy, <5% false positives"

2. KEY METRICS WITH THRESHOLDS
   - Household Size: 3-18 (normal), >25 (fraud alert)
   - IP Cardinality: 1-3 (normal), >10 (proxy alert)
   - Fragmentation: <30% (good), >60% (poor quality)

3. FRAUD DETECTION PATTERNS
   - Botnet: >20 devices, >10 IPs, 6-hour window
   - Proxy: IP rotation, geographic diversity
   - Commercial IP: >50 devices/24hrs

4. EXAMPLE INSIGHTS (GOOD vs BAD)
   Show 3 examples of high/medium/low quality

5. REPORT AUDIENCE
   - Who reads it? What decisions do they make?

Output as structured markdown with numbers and examples.
```

---

## Configuration by Use Case

### Fraud Detection
```bash
export GAE_PLATFORM_REPORTING_MIN_CONFIDENCE=0.15
export GAE_PLATFORM_MAX_LLM_INSIGHTS_PER_REPORT=8
```

### Household Identity
```bash
export GAE_PLATFORM_REPORTING_MIN_CONFIDENCE=0.25
export GAE_PLATFORM_MAX_LLM_INSIGHTS_PER_REPORT=5
```

### Inventory Ranking
```bash
export GAE_PLATFORM_REPORTING_MIN_CONFIDENCE=0.3
export GAE_PLATFORM_MAX_LLM_INSIGHTS_PER_REPORT=4
```

---

## Action Plan

**Today (30 min):**
1. Set environment variables
2. Update library
3. Re-run and check quality

**This Week (2-3 hrs):**
4. Regenerate business requirements with NotebookLM
5. Add thresholds and examples
6. Re-run with new requirements

**Next Week (4-6 hrs):**
7. Custom CSS for Premion branding
8. Add domain example insights
9. Algorithm-specific prompts

---

## What Good Looks Like

**Current (Bad):**
```
### 1. Insight
[Generic text...]
- Confidence: 30%
- Business Impact: Further analysis recommended
```

**Target (Good):**
```
### Botnet Signature: Residential Proxy Pool at Site/8448912

Component Site/8448912 has 47 IPs connected to 127 devices (15:1 ratio).
Normal: 1-3 IPs per 5-15 devices. This is 99th percentile.

Statistical Evidence:
- IP cardinality: 47 (normal: 1-3)
- Device pool: 127 (normal: 5-15)
- Connection window: 6 hours
- Geographic: 12 different subnets

Business Impact:
IMMEDIATE: Block Site/8448912. Risk: $12-18K/month IVT.
SECONDARY: Audit data source.

Confidence: 87%
```

---

## Need Help?

After applying fixes:
1. Share updated business_requirements - I'll review
2. Share a "good" cursor report - I'll match the style
3. Check logs for parsing/validation errors

The library now supports your use case but needs domain-specific inputs to generate domain-specific outputs.
