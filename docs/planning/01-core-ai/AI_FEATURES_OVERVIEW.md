# AI Features Overview

**Quick Reference for Customer Usage**

---

## What's New?

We're adding **optional** AI-assisted workflow capabilities to help you go from business requirements to actionable graph analytics insights automatically.

### ✅ Your Existing Code Still Works

**Nothing changes for existing users.** All AI features are:
- **Optional** - Disabled by default
- **Opt-in only** - Requires explicit activation
- **Non-breaking** - Zero impact on existing code
- **Separate** - In a new `ai` submodule

---

## How It Works

### Traditional Workflow (Still Available)

```python
# You manually create analysis configuration
from graph_analytics_ai import GAEOrchestrator, AnalysisConfig

config = AnalysisConfig(
    name="fraud_detection",
    vertex_collections=["customers", "transactions"],
    edge_collections=["makes_payment"],
    algorithm="pagerank"
)

orchestrator = GAEOrchestrator()
result = orchestrator.run_analysis(config)
```

### New AI-Assisted Workflow (Optional)

```python
# AI generates analysis from your business requirements
from graph_analytics_ai.ai import AIWorkflowOrchestrator

workflow = AIWorkflowOrchestrator(
    llm_provider="openrouter",
    llm_api_key=os.getenv("OPENROUTER_API_KEY")
)

# Add your business documents
workflow.add_document("fraud_detection_requirements.md")
workflow.add_document("domain_knowledge.md")

# AI does the rest
result = workflow.run_complete_workflow(
    database_name="payments_db"
)

# Review AI-generated PRD, use cases, and actionable report
```

---

## What AI Does For You

### 1. **Analyzes Your Graph Schema**
- Discovers collections and relationships
- Identifies patterns and structure
- Estimates graph size and complexity

### 2. **Processes Your Requirements**
- Extracts business objectives
- Identifies success criteria
- Understands constraints and context

### 3. **Generates Product Requirements Document**
- Maps requirements to graph analytics capabilities
- Defines technical approach
- Validates feasibility

### 4. **Creates Analytics Use Cases**
- Selects appropriate graph algorithms
- Explains business value
- Prioritizes by impact

### 5. **Generates Analysis Templates**
- Creates `AnalysisConfig` objects
- Optimizes algorithm parameters
- Selects appropriate engine sizes

### 6. **Executes Analyses**
- Runs analyses using existing GAE orchestrator
- Monitors progress
- Handles errors

### 7. **Generates Actionable Reports**
- Interprets results in business context
- Provides specific recommendations
- Explains insights and implications

---

## Your Input: Business Documents

You provide documents describing your objectives, context, and use cases:

### Example: `fraud_detection_requirements.md`

```markdown
# Fraud Detection Requirements

## Objective
Identify fraudulent transaction patterns in our payment network.

## Success Criteria
- Detect suspicious transaction clusters
- Identify high-risk accounts
- Generate alerts for investigation

## Constraints
- Must complete within 1 hour
- Budget: <$10 per analysis
```

### Example: `domain_knowledge.md`

```markdown
# Domain Context

Our payment network includes:
- Customers (verified/unverified)
- Merchants (categories, locations)
- Transactions (amounts, timestamps)

Known fraud patterns:
- Rapid transactions from single account
- Circular money transfers
```

---

## AI Output: Complete Analysis Workflow

### Generated Use Cases

```
✓ High-Risk Account Detection (PageRank)
  - Identifies highly connected accounts
  - Business Value: Flag accounts for investigation

✓ Fraud Ring Detection (WCC)
  - Finds isolated transaction clusters
  - Business Value: Detect organized fraud networks

✓ Transaction Pattern Analysis (Community Detection)
  - Groups similar patterns
  - Business Value: Identify anomalies
```

### Actionable Report

```markdown
# Fraud Detection Analysis Report

## Executive Summary
Analysis identified 23 high-risk accounts and 5 potential fraud rings.

## Key Findings
- 23 accounts with risk score >0.95 require investigation
- 5 fraud rings with 127 total participants
- Estimated fraud exposure: $1.2M

## Recommendations
1. Immediately flag high-risk accounts
2. Investigate fraud ring #1 (47 accounts, $680K volume)
3. Implement real-time monitoring
```

---

## Bring Your Own LLM

### We Support Multiple Providers

You provide your own LLM API key. We support:

#### OpenRouter (Recommended)
- **Single API** for 100+ LLM providers
- **Cost-effective**: Gemini Flash starts at $0.01/workflow
- **Flexible**: Easy to switch models
- **No vendor lock-in**

```bash
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=google/gemini-2.5-flash
LLM_PROVIDER=openrouter
```

#### OpenAI
```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
LLM_PROVIDER=openai
```

#### Anthropic
```bash
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
LLM_PROVIDER=anthropic
```

#### Custom Provider
```bash
CUSTOM_LLM_BASE_URL=https://your-llm-api.com/v1
CUSTOM_LLM_API_KEY=your-key
LLM_PROVIDER=custom
```

---

## Cost Transparency

### LLM Costs (You Control)

**Using Google Gemini 2.5 Flash (Recommended):**
- ~$0.01 per complete workflow
- ~20-35 API calls per workflow
- ~80K tokens total

**Using Anthropic Claude 3.5 Sonnet:**
- ~$0.60 per complete workflow
- Higher quality for complex scenarios

**You control costs by:**
- Choosing model (free to premium)
- Setting token limits
- Running partial workflows
- Caching results

### GAE Costs (Unchanged)

Same as current library:
- Based on engine size and runtime
- Example: e16 for 10 minutes = $0.07

### Total Example Cost

**Complete AI-assisted fraud detection workflow:**
- LLM: $0.01 (Gemini Flash)
- GAE: $0.33 (4 analyses)
- **Total: $0.34**

---

## Setup (3 Steps)

### Step 1: Get OpenRouter API Key

1. Visit https://openrouter.ai/
2. Sign up (free)
3. Create API key
4. Optional: Add credits (Gemini Flash is free/very cheap)

### Step 2: Update `.env` File

```bash
# Enable AI features
AI_WORKFLOW_ENABLED=true

# Add OpenRouter config
OPENROUTER_API_KEY=your-key-here
OPENROUTER_MODEL=google/gemini-2.5-flash
LLM_PROVIDER=openrouter
```

### Step 3: Install AI Dependencies

```bash
pip install graph-analytics-ai[ai]
```

That's it! You're ready to use AI-assisted workflows.

---

## Usage Examples

### Complete Automated Workflow

```python
from graph_analytics_ai.ai import AIWorkflowOrchestrator

workflow = AIWorkflowOrchestrator()

# Add your documents
workflow.add_document("requirements.md")
workflow.add_document("context.md")

# Run complete workflow
result = workflow.run_complete_workflow(
    database_name="my_db",
    output_dir="./analysis_output"
)

# Access results
print(f"PRD: {result.prd_path}")
print(f"Report: {result.report_path}")
print(f"Total cost: ${result.total_cost_usd:.4f}")
```

### Step-by-Step with Review

```python
workflow = AIWorkflowOrchestrator()

# Step 1: Analyze schema
schema = workflow.analyze_schema(database_name="my_db")
print(f"Graph: {schema.vertex_count:,} vertices, {schema.edge_count:,} edges")

# Step 2: Generate PRD
workflow.add_document("requirements.md")
prd = workflow.generate_prd()
print(f"Generated PRD with {len(prd.objectives)} objectives")

# Review PRD, then continue...
if input("Proceed? (y/n): ") == 'y':
    # Step 3: Generate use cases
    use_cases = workflow.generate_use_cases()
    for uc in use_cases:
        print(f"- {uc.name}: {uc.algorithm}")
    
    # Step 4: Generate templates
    templates = workflow.generate_templates()
    
    # Step 5: Execute analyses
    results = workflow.execute_analyses(templates)
    
    # Step 6: Generate report
    report = workflow.generate_report(results)
    print(f"Report saved to: {report.path}")
```

### Mix AI and Manual

```python
# Use AI for discovery, manual for execution
workflow = AIWorkflowOrchestrator()

# Let AI analyze and recommend
use_cases = workflow.generate_use_cases_from_requirements(
    requirements_path="requirements.md"
)

# Review AI suggestions
for uc in use_cases:
    print(f"{uc.name}:")
    print(f"  Algorithm: {uc.algorithm}")
    print(f"  Business Value: {uc.business_value}")

# Manually select and customize
selected = use_cases[0]  # Pick the one you want
custom_config = AnalysisConfig(
    name=selected.name,
    algorithm=selected.algorithm,
    vertex_collections=selected.vertex_collections,
    edge_collections=selected.edge_collections,
    # Customize as needed
    engine_size="e32"  # Override AI recommendation
)

# Execute manually
from graph_analytics_ai import GAEOrchestrator
orchestrator = GAEOrchestrator()
result = orchestrator.run_analysis(custom_config)
```

---

## Use Cases

### 1. Fraud Detection
**Input:** Transaction network, fraud patterns  
**AI Output:** Risk scoring, fraud ring detection, pattern analysis  
**Time Saved:** 8-16 hours → 30 minutes

### 2. Supply Chain Optimization
**Input:** Supplier network, optimization goals  
**AI Output:** Critical supplier identification, alternative paths  
**Time Saved:** 1-2 days → 1 hour

### 3. Customer Segmentation
**Input:** Customer behavior data, segmentation goals  
**AI Output:** Community detection, influence analysis  
**Time Saved:** 4-8 hours → 45 minutes

### 4. Network Analysis
**Input:** Network data, analysis objectives  
**AI Output:** Centrality analysis, bottleneck detection  
**Time Saved:** 6-12 hours → 1 hour

---

## Recommended Models

| Model | Speed | Cost/Workflow | Quality | Use Case |
|-------|-------|---------------|---------|----------|
| **google/gemini-2.0-flash-001:free** | Very Fast | Free | Good | Development, testing |
| **google/gemini-2.5-flash** | Fast (6-30s) | $0.01 | Excellent | Production default |
| **anthropic/claude-3.5-sonnet** | Medium | $0.60 | Outstanding | Complex analysis |
| **openai/gpt-4o** | Medium | $0.40 | Excellent | General purpose |

### Our Recommendation: Gemini 2.5 Flash

- **Fast:** Average 11 seconds per query
- **Cheap:** ~$0.01 per complete workflow
- **Quality:** Excellent for graph analytics tasks
- **Reliable:** Google infrastructure

---

## Benefits

### For Data Scientists
- **Faster:** Minutes instead of hours
- **Guided:** AI recommends optimal algorithms
- **Automated:** End-to-end workflow
- **Learning:** See AI reasoning

### For Analysts
- **Accessible:** No graph expertise needed
- **Actionable:** Get insights, not just data
- **Documented:** Complete PRD and report
- **Explainable:** Understand why recommendations

### For Managers
- **ROI:** 10-20x time savings
- **Consistency:** Standardized process
- **Quality:** Best practices built-in
- **Transparency:** Clear costs and reasoning

---

## FAQ

### Does this change existing library behavior?
**No.** AI features are in a separate module and disabled by default.

### Do I need to modify existing code?
**No.** Your existing code continues to work unchanged.

### Can I use it without AI features?
**Yes.** AI features are completely optional.

### Which LLM provider should I use?
**OpenRouter** for flexibility and cost-effectiveness. Start with Gemini Flash.

### How much does it cost?
**$0.01-$0.60 per workflow** for LLM (you control). GAE costs unchanged.

### What data is sent to the LLM?
**Schema metadata** (collection names, relationships) and **your documents**. No actual data values.

### Can I review before execution?
**Yes.** Enable review mode to approve each step.

### What if AI recommendations are wrong?
**You control everything.** Review, edit, or override any AI output.

### Can I use my own LLM?
**Yes.** Custom provider support included.

### Is this production-ready?
**Linear workflow:** v2.0.0 (Q3 2026)  
**Agentic workflow:** v2.2.0 (Q4 2026)

---

## Roadmap

### Phase 1: Foundation (v1.3.0) - 2 weeks
- LLM provider abstraction
- OpenRouter integration
- Basic AI infrastructure

### Phase 2-6: Core Features (v1.4.0-1.8.0) - 11 weeks
- Schema analysis
- Document processing
- PRD generation
- Use case generation
- Template generation

### Phase 7-8: Execution & Reports (v1.9.0-2.0.0) - 5 weeks
- Analysis execution
- Report generation
- Complete workflow

### Phase 9: Complete Workflow (v2.1.0) - 3 weeks
- End-to-end orchestration
- CLI interface
- Checkpoint/resume

### Phase 10: Agentic (v2.2.0) - 4 weeks
- Autonomous agents
- Adaptive execution
- Advanced reasoning

**Total: ~25 weeks (6 months)**

---

## Getting Started

### 1. Review the Full Plan
See `AGENTIC_AI_IMPLEMENTATION_PLAN.md` for complete details.

### 2. Set Up OpenRouter
- Visit https://openrouter.ai/
- Create account and API key
- Add key to `.env` file

### 3. Try the Examples
Once implemented, start with examples in `examples/ai_workflow.py`

### 4. Provide Feedback
Help us improve by sharing your experience and suggestions.

---

## Support

### Documentation
- **Full Plan:** `AGENTIC_AI_IMPLEMENTATION_PLAN.md`
- **API Reference:** `AI_API_REFERENCE.md` (coming soon)
- **Examples:** `examples/ai_workflow.py` (coming soon)

### Questions?
- Open GitHub issue with `[AI Features]` tag
- See FAQ section above
- Check documentation

---

## Summary

**✅ Backward Compatible:** Your existing code works unchanged  
**✅ Opt-In Only:** AI features are completely optional  
**✅ Customer Controlled:** You provide and control LLM  
**✅ Cost Effective:** ~$0.01 per workflow with Gemini Flash  
**✅ Time Saving:** 10-20x faster than manual approach  
**✅ High Quality:** Leverages best practices and LLM reasoning  
**✅ Flexible:** Use complete automation or step-by-step  
**✅ Transparent:** Clear costs, reasoning, and outputs  

**Ready to transform business requirements into graph analytics insights automatically.**
