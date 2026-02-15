# Quick Reference: Customer Project Setup

**Use this as a quick guide for creating customer projects that use the graph-analytics-ai library**

---

## Step 1: Create Project Directory

```bash
cd ~/code
mkdir customer-graph-analytics # Replace 'customer' with actual name
cd customer-graph-analytics
mkdir -p {docs,scripts,config,outputs,notebooks}
```

---

## Step 2: Create requirements.txt

```txt
# Install library from local path (development)
-e ../agentic-graph-analytics

# Or from PyPI (when published)
# graph-analytics-ai>=3.0.0
```

Install: `pip install -r requirements.txt`

---

## Step 3: Create Main Script

**File:** `scripts/run_analysis.py`

```python
#!/usr/bin/env python3
"""
Customer Graph Analytics Workflow
"""
from pathlib import Path
from graph_analytics_ai.ai.agents.runner import AgenticWorkflowRunner
from graph_analytics_ai.db_connection import get_db_connection

def main():
 # Load requirements document
 docs_dir = Path(__file__).parent.parent / "docs"
 requirements_file = docs_dir / "business_requirements.md"
 
 with open(requirements_file, 'r') as f:
 requirements_content = f.read()
 
 # Initialize agentic workflow runner
 runner = AgenticWorkflowRunner(
 db_connection=get_db_connection(),
 graph_name="YourGraphName" # Change this
 )
 
 # Run workflow
 final_state = runner.run(
 input_documents=[{
 "path": str(requirements_file),
 "content": requirements_content,
 "type": "text/markdown"
 }],
 max_executions=3
 )
 
 # Display results
 print(f" Workflow Complete!")
 print(f"Status: {final_state.status}")
 print(f"Reports: {len(final_state.reports)}")
 
 return final_state

if __name__ == "__main__":
 main()
```

---

## Step 4: Create .env File

```bash
# ArangoDB Configuration
ARANGO_ENDPOINT=https://your-cluster.arangodb.cloud:8529
ARANGO_DATABASE=your_database
ARANGO_USER=root
ARANGO_PASSWORD=your_password

# GAE Configuration
GAE_DEPLOYMENT_MODE=amp
ARANGO_GRAPH_API_KEY_ID=your_api_key_id
ARANGO_GRAPH_API_KEY_SECRET=your_api_key_secret

# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4
```

---

## Step 5: Create Business Requirements

**File:** `docs/business_requirements.md`

### Pro Tip: Include Domain Description

**Adding a domain description section dramatically improves AI recommendations (15-25% better accuracy)!**

See `examples/requirements_template.md` for a complete template, or use this quick version:

```markdown
# Customer Graph Analytics Use Cases

## Domain Description

### Industry & Business Context
[1-2 sentences: What industry? What does your organization do?]

### Graph Structure Overview
**Nodes:** [What entities exist? Include approximate counts]
- Users (50K): [who they are]
- Products (200K): [what they represent]
- [Other node types...]

**Edges:** [What relationships connect them?]
- Purchases: User → Product (transactions)
- [Other edge types...]

**Scale:** [Key metrics]
- [Transactions per month]
- [Active users]
- [Historical data depth]

### Domain-Specific Terms
- **[Term 1]**: [Definition in your context]
- **[Term 2]**: [Definition in your context]

### Business Context
[What are you trying to achieve? What problems are you solving?]

---

## Business Objectives

### Objective 1: [Name]
**Priority:** [Critical | High | Medium | Low]
**Goal:** [What you want to achieve]
**Success Criteria:** 
- [Measurable criterion 1]
- [Measurable criterion 2]
**Expected Value:** [Quantified impact]

### Objective 2: [Name]
...

---

## Requirements

### REQ-001: [Title]
**Description:** [What analysis is needed]
**Business Question:** [What question does this answer?]
**Outputs Needed:**
- [Output 1]
- [Output 2]
- **Report Format:** [Interactive HTML (Plotly) | Markdown | JSON] (choose one or more)

### REQ-002: [Title]
...
```

**Why Domain Description Matters:**
- 15-25% improvement in recommendation accuracy
- More contextual insights in reports
- Better algorithm matching to your business needs
- Domain-specific terminology in outputs
- ⏱ Takes only 5-10 minutes to write
- Makes AI "understand" your business

**Quick Example:**
```markdown
## Domain Description

### Industry & Business Context
E-commerce fashion marketplace connecting 1,000 brands with millions of consumers.

### Graph Structure Overview
**Nodes:** Customers (50K), Products (200K), Brands (1K)
**Edges:** Purchases (500K/month), Reviews (100K/month), Follows (250K)
**Scale:** $5M monthly GMV, 50K daily active users

### Domain Terms
- **Influencer**: Customer with 100+ followers driving purchases
- **Conversion**: View → Purchase rate
- **Engagement**: Reviews + shares + follows

### Business Context
Growing 100% YoY but poor retention. Need to identify influencers 
to focus marketing and reduce acquisition costs by 40%.
```

**Don't have all the details?** That's okay! The AI works with what you provide. 
Even a brief description is much better than none.

**See:** `examples/use_case_document.md` for a complete example with domain description.

---

## Step 6: Test Setup

```bash
# Test library import
python -c "from graph_analytics_ai.ai.agents.runner import AgenticWorkflowRunner; print(' Import successful')"

# Test database connection
python -c "from graph_analytics_ai.db_connection import get_db_connection; db = get_db_connection(); print(f' Connected to {db.name}')"

# Run workflow
python scripts/run_analysis.py
```

---

## Directory Structure

```
customer-graph-analytics/
 README.md
 requirements.txt
 .env
 docs/
 business_requirements.md
 scripts/
 run_analysis.py
 config/
 outputs/
 notebooks/
```

---

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run analysis
python scripts/run_analysis.py

# Activate virtual environment (if using one)
source venv/bin/activate # or venv\Scripts\activate on Windows

# Update library (if installed in editable mode)
cd ../agentic-graph-analytics
git pull
pip install -e .
```

---

## Workflow Modes

### Option 1: Agentic Workflow (Recommended)
```python
from graph_analytics_ai.ai.agents.runner import AgenticWorkflowRunner

runner = AgenticWorkflowRunner(graph_name="MyGraph")
state = runner.run()
```

**Benefits:** Autonomous, self-healing, explainable AI

### Option 2: Traditional Orchestrator
```python
from graph_analytics_ai.ai.workflow.orchestrator import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator(graph_name="MyGraph")
result = orchestrator.run_complete_workflow(input_files=["requirements.pdf"])
```

**Benefits:** Step-by-step control, easy debugging

---

## Troubleshooting

### Import Error
```bash
# Check installation
pip show graph-analytics-ai

# Reinstall
pip install -e ../agentic-graph-analytics --force-reinstall
```

### Connection Error
```bash
# Verify .env file exists
cat .env

# Test connection
python -c "from graph_analytics_ai.db_connection import get_db_connection; get_db_connection()"
```

### Module Not Found
```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Ensure you're in correct directory
pwd
```

---

## Best Practices

1. **Always use the library** - Import from `graph_analytics_ai`
2. **Never bypass the workflow** - Use `AgenticWorkflowRunner` or `WorkflowOrchestrator`
3. **Keep customer code separate** - Don't modify the library
4. **Use .env for credentials** - Never commit credentials
5. **Document your use cases** - Write clear business requirements
6. **Version control** - Use git for your customer project

---

## What NOT to Do

 **Don't modify the library** - Keep it clean and reusable 
 **Don't bypass the workflow** - Use the agentic system 
 **Don't hardcode templates** - Let the agents generate them 
 **Don't make direct GAE calls** - Use the workflow 
 **Don't commit credentials** - Use .env files 

---

## Need Help?

1. Check library documentation: `agentic-graph-analytics/README.md`
2. Review examples: `agentic-graph-analytics/examples/`
3. Read archived migration plan: `docs/archive/premion-use-case/PREMION_MIGRATION_PLAN.md`
4. Check archived cleanup summary: `docs/archive/premion-use-case/CLEANUP_SUMMARY.md`

---

**Pattern:** Library (reusable) + Customer Project (specific) 
**Result:** Clean, maintainable, scalable architecture

