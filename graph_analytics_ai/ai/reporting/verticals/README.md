# Platform Custom Verticals Registry

This directory contains custom industry verticals that have been promoted from client projects to the platform for sharing across multiple projects.

---

## Directory Structure

```
verticals/
  eda_ic_design.json      ← Custom vertical for IC Design & EDA
  README.md              ← This file
```

---

## What Are Platform Custom Verticals?

**Platform custom verticals** are high-quality custom verticals that:
- Started as project-specific verticals (`.graph-analytics/industry_vertical.json`)
- Were tested and validated in real projects
- Are valuable enough to share across multiple projects
- Have been "promoted" to the platform registry

---

## Load Priority

When a workflow requests an industry vertical, the platform checks in this order:

1. **Client project custom vertical** (`.graph-analytics/industry_vertical.json`)
2. **Platform custom vertical** (this directory)
3. **Built-in vertical** (hardcoded in `prompts.py`)

This means:
- Client projects can override platform verticals with their own customizations
- Platform verticals are available as defaults for new projects
- Built-in verticals are always available as fallback

---

## How to Promote a Vertical

### From CLI (Future - Phase 4)

```bash
cd ~/code/your-project

# Promote your custom vertical to platform
python -m graph_analytics_ai.cli.promote-vertical \
  --source .graph-analytics/industry_vertical.json \
  --name supply_chain \
  --description "Supply chain and logistics analytics"
```

### Manually (Phase 1 - Current)

```bash
# 1. Verify your vertical is high quality
cat .graph-analytics/industry_vertical.json

# 2. Copy to platform verticals directory
cp .graph-analytics/industry_vertical.json \
   ~/code/agentic-graph-analytics/graph_analytics_ai/ai/reporting/verticals/supply_chain.json

# 3. Commit to platform repo
cd ~/code/agentic-graph-analytics
git add graph_analytics_ai/ai/reporting/verticals/supply_chain.json
git commit -m "Add supply chain custom vertical to platform registry"
git push
```

---

## Quality Guidelines for Promotion

Before promoting a vertical to the platform, ensure:

### ✅ Quality Checklist

- [ ] Tested in at least one real project
- [ ] Generated insights are high quality (specific, actionable)
- [ ] Prompt is comprehensive (1500+ words)
- [ ] Pattern definitions are well-defined (2+ per algorithm)
- [ ] Domain terminology is accurate
- [ ] No sensitive/proprietary information
- [ ] JSON is valid and well-formatted
- [ ] `user_validated: true` in metadata
- [ ] User notes document any refinements made

### 📝 Review Criteria

**Prompt Quality:**
- Uses domain-specific terminology correctly
- Includes concrete examples
- Provides actionable guidance
- Defines clear risk levels
- Includes output format guidance

**Pattern Quality:**
- Specific and detectable
- Relevant to domain
- Clear indicators listed
- Appropriate risk levels
- Actionable business impact

**Documentation:**
- Clear metadata (name, display name, version)
- Source documents listed
- Generation date included
- User notes document refinements

---

## Example: Promoting Supply Chain Vertical

### 1. Generate in Project

```bash
cd ~/code/supply-chain-project

python -m graph_analytics_ai.cli.generate_vertical \
  --input docs/business_requirements.md \
  --graph-name supply_chain_graph
```

**Creates:** `.graph-analytics/industry_vertical.json`

### 2. Test and Refine

```python
# Run workflow with custom vertical
runner = AgenticWorkflowRunner(
    graph_name="supply_chain_graph",
    industry="supply_chain"
)
state = await runner.run_async()

# Review reports - are insights good?
# If not, edit .graph-analytics/industry_vertical.json
# Refine prompt, adjust patterns, re-run
```

### 3. Mark as Validated

```bash
# Edit .graph-analytics/industry_vertical.json
# Change: "user_validated": false → "user_validated": true
# Add: "user_notes": "Tested on 3 supply chain graphs, good quality"
```

### 4. Promote to Platform

```bash
cp .graph-analytics/industry_vertical.json \
   ~/code/agentic-graph-analytics/graph_analytics_ai/ai/reporting/verticals/supply_chain.json

cd ~/code/agentic-graph-analytics
git add graph_analytics_ai/ai/reporting/verticals/supply_chain.json
git commit -m "Add supply chain vertical to platform registry

Tested in supply-chain-project with good results.
Detects single points of failure, geographic concentration, etc."
git push
```

### 5. Now Available to All Projects

```python
# Any project can now use supply_chain vertical
# (even without .graph-analytics/industry_vertical.json)

runner = AgenticWorkflowRunner(
    graph_name="any_supply_chain_graph",
    industry="supply_chain"  # Loads from platform registry
)
```

---

## Listing Available Verticals

```python
from graph_analytics_ai.ai.reporting import list_all_verticals

verticals = list_all_verticals()

print("Built-in Verticals:")
for v in verticals["builtin"]:
    print(f"  - {v}")

print("\nPlatform Custom Verticals:")
for v in verticals["platform_custom"]:
    print(f"  - {v['name']}: {v['display_name']}")

if verticals["project_custom"]:
    print(f"\nProject Custom Vertical:")
    pc = verticals["project_custom"]
    print(f"  - {pc['name']}: {pc['display_name']}")
    print(f"    Generated: {pc['generated_at']}")
    print(f"    Validated: {pc['user_validated']}")
```

---

## Current Verticals in Registry

As of February 11, 2026:

**Built-in Verticals (5):**
- adtech (Ad-Tech / Identity Resolution)
- fintech (FinTech / Financial Services)
- fraud_intelligence (Fraud Intelligence - Indian Banking)
- social (Social Networks)
- generic (Generic Analysis)

**Platform Custom Verticals (1):**
- eda_ic_design (Integrated Circuit (IC) Design & Electronic Design Automation (EDA))

---

## Contributing

Want to contribute a high-quality custom vertical to the platform?

1. Generate and test in your project
2. Ensure it meets quality guidelines
3. Open a PR with the vertical JSON
4. Include:
   - Example business requirements used
   - Sample generated insights
   - Test results
   - Use cases

---

## Future Enhancements

**Phase 2 (Coming Soon):**
- Better prompt generation with few-shot examples
- Interactive refinement workflow
- Quality scoring

**Phase 3:**
- Generate Python pattern detector code
- Safe execution sandbox
- Advanced customization

**Phase 4:**
- Community registry/marketplace
- Version management
- Vertical inheritance

---

**Documentation:**
- Proposal: `docs/proposals/AUTO_GENERATE_CUSTOM_VERTICALS.md`
- Quick Start: `docs/guides/CUSTOM_VERTICALS_QUICKSTART.md`
- Template: `templates/business_requirements_template.md`

**Status:** Phase 1 MVP - Ready for Testing
