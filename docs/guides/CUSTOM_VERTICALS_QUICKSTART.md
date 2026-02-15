# Custom Industry Verticals - Quick Start

**Feature Status:** Phase 1 MVP - Basic Implementation

---

## What This Is

Automatically generate custom industry verticals from your business requirements document. No need to modify platform code to add new industries!

---

## Quick Start

### 1. Create Enhanced Business Requirements

Use the template at `templates/business_requirements_template.md`

**Key sections to fill out:**
- Domain Overview (industry, business function)
- Domain Terminology (currency, units, regulations, thresholds)
- Graph Structure (nodes and edges)
- Key Metrics & KPIs
- Patterns to Detect
- Reporting & Deliverables (interactive HTML vs markdown vs JSON)
- **Example Insights** (most important - shows what good looks like)

### 2. Generate Your Custom Vertical

```bash
cd ~/code/your-project

# Generate from business requirements
python -m graph_analytics_ai.cli.generate_vertical \
  --input docs/business_requirements.md \
  --graph-name your_graph_name \
  --validate \
  --interactive
```

**Output:** `.graph-analytics/industry_vertical.json`

### 3. Use in Your Workflow

```python
from graph_analytics_ai.ai.agents import AgenticWorkflowRunner

# The runner will automatically detect and load the custom vertical
runner = AgenticWorkflowRunner(
    graph_name="your_graph_name",
    industry="your_industry_name"  # Matches the name in vertical JSON
)

state = await runner.run_async(
    input_files=["docs/business_requirements.md"]
)
```

**That's it!** The platform automatically finds and uses your custom vertical.

---

## How It Works

```
1. You create: docs/business_requirements.md (comprehensive)
2. You run: python -m graph_analytics_ai.cli.generate_vertical
3. Platform generates: .graph-analytics/industry_vertical.json
4. You review and edit: Add refinements if needed
5. You run workflow: Uses custom vertical automatically
6. Platform generates: Domain-specific insights!
```

---

## Example

### Input: Supply Chain Business Requirements

```markdown
# Supply Chain Requirements

## 1. Domain Overview
Industry: Supply Chain & Logistics
Primary Function: Detect supply chain bottlenecks and single points of failure

## 3. Graph Structure
Nodes: Supplier, Warehouse, Product, ShipmentRoute
Edges: suppliesTo, stores, shipsVia, dependsOn

## 5. Patterns to Detect
**Single Point of Failure:**
- One supplier with no backup
- > 30% production depends on it
- Business Impact: Production halt if fails

## 8. Example Insights
Title: Single Point of Failure - Supplier S-123
Description: Sole provider of Component X (40% of products)...
Business Impact: $2.4M/week at risk, need backup suppliers...
```

### Output: .graph-analytics/industry_vertical.json

```json
{
  "metadata": {
    "name": "supply_chain",
    "display_name": "Supply Chain & Logistics",
    "version": "1.0"
  },
  "analysis_prompt": "You are analyzing a supply chain graph...\n\nDetect patterns like:\n- Single points of failure (critical suppliers)\n- Geographic concentration risks\n...",
  "pattern_definitions": {
    "wcc": [
      {
        "name": "single_point_of_failure",
        "description": "Critical supplier with no alternatives",
        "risk_level": "CRITICAL"
      }
    ]
  }
}
```

### Result: Domain-Specific Insights

```
Report: Supply Chain Risk Analysis

Insights:
  [CRITICAL] Single Point of Failure: Supplier S-456
    • Sole provider of hydraulic components (45% of product line)
    • No backup suppliers identified
    • Current inventory: 8 days (below 7-day critical threshold)
    • Financial exposure: $3.2M/week if disrupted
    
    IMMEDIATE: Flag for enhanced monitoring, audit inventory daily
    SHORT-TERM: Identify 2 backup suppliers within 45 days
    LONG-TERM: Implement dual-sourcing for all critical components
    
    Confidence: 0.89
```

---

## File Structure

### Your Project

```
your-project/
  .graph-analytics/                    ← NEW: Config directory
    industry_vertical.json             ← Your custom vertical
  docs/
    business_requirements.md           ← Enhanced with new sections
    domain_description.md              ← Optional
  run_analysis.py                      ← Your analysis script
```

### Platform (for reference)

```
agentic-graph-analytics/
  graph_analytics_ai/
    ai/
      agents/
        industry_vertical.py           ← NEW: Generation agent
      reporting/
        custom_verticals.py            ← NEW: Loading utilities
        vertical_schema.py             ← NEW: JSON schema
        verticals/                     ← NEW: Platform registry (future)
  templates/
    business_requirements_template.md  ← NEW: Enhanced template
  cli/
    generate_vertical.py               ← NEW: CLI command
```

---

## Commands

### Generate Vertical

```bash
# Basic
python -m graph_analytics_ai.cli.generate_vertical \
  --input docs/business_requirements.md \
  --graph-name my_graph

# With all options
python -m graph_analytics_ai.cli.generate_vertical \
  --input docs/business_requirements.md \
  --domain-description docs/domain_description.md \
  --graph-name my_graph \
  --output .graph-analytics/industry_vertical.json \
  --base-vertical fintech \
  --validate \
  --interactive
```

### List All Verticals

```python
from graph_analytics_ai.ai.reporting import list_all_verticals

verticals = list_all_verticals()
print("Built-in:", verticals["builtin"])
print("Platform Custom:", verticals["platform_custom"])
print("Project Custom:", verticals["project_custom"])
```

### Load Custom Vertical

```python
from pathlib import Path
from graph_analytics_ai.ai.reporting import load_custom_vertical

# Load from project
vertical = load_custom_vertical(Path.cwd())
if vertical:
    print(f"Found: {vertical['metadata']['display_name']}")
```

---

## Phase 1 MVP Features

### ✅ Implemented

- [x] JSON schema for custom verticals
- [x] IndustryVerticalAgent (basic generation)
- [x] Custom vertical loading from project
- [x] Registration with platform
- [x] CLI: generate-vertical command
- [x] Enhanced business requirements template
- [x] Test script

### 🚧 Coming in Phase 2

- [ ] Better prompt quality with examples
- [ ] Interactive refinement workflow
- [ ] Pattern detector code generation
- [ ] Platform registry for sharing
- [ ] CLI: validate-vertical command
- [ ] CLI: promote-vertical command
- [ ] Integration with AgenticWorkflowRunner

---

## Testing

### Test Vertical Generation

```bash
cd ~/code/agentic-graph-analytics
python test_custom_vertical.py
```

**Expected output:**
- Generates sample supply chain vertical
- Saves to `test_vertical_output/supply_chain_vertical.json`
- Shows summary and prompt excerpt

### Test with Real Project

```bash
cd ~/code/your-project

# Make sure you have enhanced business requirements
# (see templates/business_requirements_template.md)

python -m graph_analytics_ai.cli.generate_vertical \
  --input docs/business_requirements.md \
  --graph-name your_graph \
  --validate \
  --interactive
```

---

## Tips for Best Results

### 1. Provide Detailed Example Insights (Section 8)

**This is the most important section!** The more detailed and realistic your example insights are, the better the generated prompt will be.

**Good example:**
```
Title: Specific Pattern Name with Numbers
Description: 500+ words with entity IDs, percentages, context
Business Impact: Specific actions with timelines and financial impact
Confidence: 0.85+
```

### 2. Be Specific About Terminology

Don't just say "currency: USD". Add context:
```
Currency: USD millions for revenue, USD for costs
Units: pallets (inventory), days (lead time), percentage (fill rate)
```

### 3. Define Clear Risk Levels

```
CRITICAL: Production halt, > $1M impact, 0-4 hour response
HIGH: Significant disruption, > $100K impact, 24-48 hour response
```

### 4. Include Domain-Specific Regulations

```
Regulations:
- Import/Export Compliance: Required documentation for international shipments
- Customs: Duty calculations and border clearance requirements
- FDA: Regulations for pharmaceutical product handling
```

---

## Troubleshooting

### "No custom vertical found"

**Cause:** File doesn't exist at `.graph-analytics/industry_vertical.json`

**Fix:** Run `generate_vertical` command first

### "Validation failed"

**Cause:** Generated JSON doesn't match schema

**Fix:** Review the JSON, fix errors manually, or use `--force` to save anyway

### "Low quality prompt generated"

**Cause:** Business requirements lack detail, especially example insights

**Fix:** 
1. Add detailed example insights (section 8)
2. Expand terminology and patterns sections
3. Regenerate

### "Wrong industry key in vertical"

**Cause:** LLM extracted incorrect name from requirements

**Fix:** Edit `.graph-analytics/industry_vertical.json` and change `metadata.name`

---

## Next Steps

### For Users

1. ✅ Try generating a vertical with the sample test script
2. ✅ Enhance your business requirements document
3. ✅ Generate your custom vertical
4. ✅ Review and refine the JSON
5. ✅ Use in your workflow

### For Development

**Phase 2 Goals:**
- Integrate with AgenticWorkflowRunner (auto-detect and generate)
- Add validation CLI command
- Improve prompt generation quality
- Add more example verticals

**Phase 3 Goals:**
- Generate actual Python pattern detector code
- Platform registry for sharing verticals
- Version management
- Community contributions

---

## Documentation

- **Proposal:** `docs/proposals/AUTO_GENERATE_CUSTOM_VERTICALS.md`
- **Template:** `templates/business_requirements_template.md`
- **Schema:** `graph_analytics_ai/ai/reporting/vertical_schema.py`
- **This Guide:** `docs/guides/CUSTOM_VERTICALS_QUICKSTART.md`

---

**Status:** Phase 1 MVP Ready for Testing  
**Date:** February 10, 2026
