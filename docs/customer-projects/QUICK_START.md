# Quick Reference: Customer Project Setup

**Use this as a quick guide for creating customer projects that use the graph-analytics-ai library**

---

## Step 1: Create Project Directory

```bash
cd ~/code
mkdir customer-graph-analytics  # Replace 'customer' with actual name
cd customer-graph-analytics
mkdir -p {docs,scripts,config,outputs,notebooks}
```

---

## Step 2: Create requirements.txt

```txt
# Install library from local path (development)
-e ../graph-analytics-ai-platform

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
        graph_name="YourGraphName"  # Change this
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
    print(f"✅ Workflow Complete!")
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

```markdown
# Customer Graph Analytics Use Cases

## Business Objective
[Describe what you want to achieve]

## Use Cases

### Use Case 1: [Name]
**Algorithm:** [e.g., PageRank, WCC, etc.]
**Description:** [What business problem does this solve?]
**Value:** [What is the expected business impact?]

### Use Case 2: [Name]
...
```

---

## Step 6: Test Setup

```bash
# Test library import
python -c "from graph_analytics_ai.ai.agents.runner import AgenticWorkflowRunner; print('✅ Import successful')"

# Test database connection
python -c "from graph_analytics_ai.db_connection import get_db_connection; db = get_db_connection(); print(f'✅ Connected to {db.name}')"

# Run workflow
python scripts/run_analysis.py
```

---

## Directory Structure

```
customer-graph-analytics/
├── README.md
├── requirements.txt
├── .env
├── docs/
│   └── business_requirements.md
├── scripts/
│   └── run_analysis.py
├── config/
├── outputs/
└── notebooks/
```

---

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run analysis
python scripts/run_analysis.py

# Activate virtual environment (if using one)
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Update library (if installed in editable mode)
cd ../graph-analytics-ai-platform
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
pip install -e ../graph-analytics-ai-platform --force-reinstall
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

1. ✅ **Always use the library** - Import from `graph_analytics_ai`
2. ✅ **Never bypass the workflow** - Use `AgenticWorkflowRunner` or `WorkflowOrchestrator`
3. ✅ **Keep customer code separate** - Don't modify the library
4. ✅ **Use .env for credentials** - Never commit credentials
5. ✅ **Document your use cases** - Write clear business requirements
6. ✅ **Version control** - Use git for your customer project

---

## What NOT to Do

❌ **Don't modify the library** - Keep it clean and reusable  
❌ **Don't bypass the workflow** - Use the agentic system  
❌ **Don't hardcode templates** - Let the agents generate them  
❌ **Don't make direct GAE calls** - Use the workflow  
❌ **Don't commit credentials** - Use .env files  

---

## Need Help?

1. Check library documentation: `graph-analytics-ai-platform/README.md`
2. Review examples: `graph-analytics-ai-platform/examples/`
3. Read archived migration plan: `docs/archive/premion-use-case/PREMION_MIGRATION_PLAN.md`
4. Check archived cleanup summary: `docs/archive/premion-use-case/CLEANUP_SUMMARY.md`

---

**Pattern:** Library (reusable) + Customer Project (specific)  
**Result:** Clean, maintainable, scalable architecture

