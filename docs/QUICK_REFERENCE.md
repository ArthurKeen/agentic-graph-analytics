# Quick Reference Guide

**Last Updated**: December 22, 2025

Complete quick reference for the Graph Analytics AI Platform. For detailed documentation, see the [Documentation Index](docs/README.md).

---

## 📦 Installation

```bash
# Basic installation
pip install -e .

# With interactive charts (recommended)
pip install -e . plotly

# Development dependencies
pip install -r requirements-dev.txt
```

---

## ⚙️ Environment Setup

### Quick Setup

```bash
# Copy example environment file
cp .env.example .env

# Edit with your credentials
vim .env
```

### Required Variables

```env
# ArangoDB Connection
ARANGO_DATABASE=your_database
ARANGO_USER=root
ARANGO_PASSWORD=your_password
ARANGO_ENDPOINT=https://your-cluster.arangodb.cloud:8529

# For GAE (Graph Analytics Engine)
GAE_DEPLOYMENT_MODE=amp
ARANGO_GRAPH_API_KEY_ID=your_api_key_id
ARANGO_GRAPH_API_KEY_SECRET=your_api_key_secret

# LLM Provider (choose one)
LLM_PROVIDER=openrouter  # or: openai, anthropic, gemini

# OpenRouter (recommended)
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=google/gemini-flash-1.5-8b

# OR OpenAI
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4

# OR Anthropic
ANTHROPIC_API_KEY=your_key
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# OR Google Gemini
GOOGLE_API_KEY=your_key
GEMINI_MODEL=gemini-pro
```

### Test Connection

```bash
python test_connection.py

# Expected output:
# ✅ Successfully connected to ArangoDB!
#    Database Name: your_database
```

### For Customer Projects

See [Environment Setup Guide](ENV_SETUP_GUIDE.md) for detailed instructions on separating test and production credentials.

---

## 🚀 Quick Start

### Agentic Workflow (Recommended)

```python
from graph_analytics_ai.ai.agents import AgenticWorkflowRunner

# Initialize runner
runner = AgenticWorkflowRunner(
    db_connection=db,
    llm_provider=llm,
    core_collections=["users", "products"],  # Main entities
    satellite_collections=["metadata"]        # Reference data
)

# Run complete workflow
result = runner.run(
    use_case_file="requirements.md",
    output_dir="./output"
)

# Reports with interactive charts automatically generated!
# Location: ./output/reports/*.html
```

### Traditional Workflow

```python
from graph_analytics_ai.ai.workflow import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator(graph_name="your_graph")

result = orchestrator.run_complete_workflow(
    input_files=["requirements.pdf"]
)

print(f"Generated {len(result.reports)} reports")
```

---

## 📊 Interactive HTML Reports

### Generate Reports with Charts

```python
from graph_analytics_ai.ai.reporting import ReportGenerator, HTMLReportFormatter

# Charts enabled by default
generator = ReportGenerator(enable_charts=True)
report = generator.generate_report(execution_result, context={
    "use_case": {"title": "Your Analysis"},
    "requirements": {"domain": "your domain"}
})

# Format as HTML
html_formatter = HTMLReportFormatter()
charts = report.metadata.get('charts', {})
html_content = html_formatter.format_report(report, charts=charts)

# Save
with open('report.html', 'w') as f:
    f.write(html_content)
```

### Chart Types by Algorithm

| Algorithm | Charts Generated |
|-----------|-----------------|
| **PageRank** | Top influencers, distribution, cumulative influence |
| **WCC** | Component sizes, distribution, connectivity pie chart |
| **Betweenness** | Bridge nodes, centrality distribution |
| **Label Propagation** | Communities, size distribution |

### Disable Charts

```python
# Generate markdown only
generator = ReportGenerator(enable_charts=False)
```

**Full Guide**: [Interactive Report Generation](docs/INTERACTIVE_REPORT_GENERATION.md)

---

## 🎯 Collection Selection

### Specify Core vs Satellite Collections

```python
from graph_analytics_ai.ai.templates import TemplateGenerator

generator = TemplateGenerator(
    graph_name="your_graph",
    satellite_collections=["metadata", "configs", "lookups"],  # Exclude from WCC/SCC
    core_collections=["users", "products", "orders"]           # Main entities
)

templates = generator.generate_templates(use_cases, schema)
```

### What Gets Selected?

| Algorithm | Satellites? | Collections Used | Why |
|-----------|-------------|------------------|-----|
| **WCC** | ❌ Excluded | Core only | Find meaningful components |
| **SCC** | ❌ Excluded | Core only | Strongly connected core |
| **PageRank** | ✅ Included | Everything | Full graph importance |
| **Betweenness** | ✅ Included | Everything | Accurate centrality |
| **Label Propagation** | ❌ Excluded | Core only | Community detection |

### Test Before Executing

```python
from graph_analytics_ai.ai.templates import select_collections_for_algorithm, AlgorithmType

# Preview WCC selection
wcc = select_collections_for_algorithm(
    AlgorithmType.WCC,
    schema,
    satellite_collections=["metadata"]
)

print(f"WCC uses: {wcc.vertex_collections}")
print(f"WCC excludes: {wcc.excluded_vertices}")
```

**Full Guide**: [Collection Selection Guide](docs/COLLECTION_SELECTION_GUIDE.md)

---

## 🔍 Workflow Tracing

### Enable Tracing

```python
from graph_analytics_ai.ai.agents import AgenticWorkflowRunner

runner = AgenticWorkflowRunner(
    db_connection=db,
    llm_provider=llm,
    enable_tracing=True,      # Enable comprehensive tracing
    enable_debug_mode=True    # Extra verbose logging
)

result = runner.run("use_cases.md")

# Print trace summary
runner.print_trace_summary()

# Export trace
runner.export_trace("trace.json", format="json")
runner.export_trace("trace.html", format="html")
```

### Trace Formats

- **JSON** - Structured data for analysis
- **HTML** - Interactive timeline visualization
- **SVG** - Workflow diagram
- **Debug Log** - Detailed text log

**Full Guide**: [Workflow Tracing Guide](docs/WORKFLOW_TRACING_GUIDE.md)

---

## 🧪 Common Tasks

### Run Tests

```bash
# All tests
pytest

# Specific module
pytest tests/unit/ai/templates/

# With coverage
pytest --cov=graph_analytics_ai

# Integration tests (requires DB)
pytest tests/integration/
```

### Run Examples

```bash
# Agentic workflow demo
python examples/agentic_workflow_example.py

# Chart generation
python examples/chart_report_example.py

# Basic usage
python examples/basic_usage.py
```

### Generate Documentation

```bash
# API documentation
pdoc graph_analytics_ai --html --output-dir docs/api/

# Or use Sphinx
cd docs/
make html
```

---

## 🔧 Troubleshooting

### Connection Issues

```bash
# Test database connection
python test_connection.py

# Check environment variables
python -c "import os; from dotenv import load_dotenv; load_dotenv(); \
           print(f'DB: {os.getenv(\"ARANGO_DATABASE\")}'); \
           print(f'Endpoint: {os.getenv(\"ARANGO_ENDPOINT\")}')"
```

### Module Not Found

```bash
# Install in editable mode
pip install -e .

# Or reinstall
pip uninstall graph-analytics-ai
pip install -e .
```

### Charts Not Generating

```bash
# Check if plotly is installed
python -c "import plotly; print('✅ Plotly available')"

# If not, install it
pip install plotly
```

### LLM API Errors

```bash
# Check API key is set
python -c "import os; from dotenv import load_dotenv; load_dotenv(); \
           print(f'LLM Provider: {os.getenv(\"LLM_PROVIDER\")}'); \
           print(f'API Key Set: {bool(os.getenv(\"OPENROUTER_API_KEY\"))}')"
```

---

## 📚 Documentation Links

### Getting Started
- [Project Overview](docs/getting-started/PROJECT_OVERVIEW.md)
- [Quick Start](docs/getting-started/QUICK_START.md)
- [Environment Setup Guide](ENV_SETUP_GUIDE.md)

### User Guides
- [Agentic Workflow](docs/user-guide/AGENTIC_WORKFLOW.md)
- [Interactive Reports](docs/INTERACTIVE_REPORT_GENERATION.md)
- [Collection Selection](docs/COLLECTION_SELECTION_GUIDE.md)
- [Workflow Tracing](docs/WORKFLOW_TRACING_GUIDE.md)
- [Execution Reporting](docs/EXECUTION_REPORTING_GUIDE.md)

### For Customer Projects
- [Customer Project Instructions](docs/CUSTOMER_PROJECT_INSTRUCTIONS.md)
- [Quick Start for Customers](CUSTOMER_PROJECT_QUICK_START.md)

### Development
- [Contributing](docs/development/CONTRIBUTING.md)
- [Testing](docs/development/TESTING.md)
- [Code Quality](docs/development/CODE_QUALITY.md)
- [Roadmap](docs/development/ROADMAP.md)

### API Reference
- [Result Management](api-reference/RESULT_MANAGEMENT_API.md)
- [Workflow Orchestration](api-reference/WORKFLOW_ORCHESTRATION.md)

---

## 🎯 Quick Commands

```bash
# Development
pytest                    # Run tests
pytest --cov             # With coverage
python setup.py sdist    # Build distribution

# Testing
python test_connection.py              # Test DB connection
python examples/agentic_workflow_example.py  # Run demo
python examples/chart_report_example.py      # Generate charts

# Documentation
cd docs && make html     # Generate Sphinx docs
pdoc graph_analytics_ai  # Generate API docs

# Git
git status              # Check status
git add .               # Stage changes
git commit -m "msg"     # Commit
git push                # Push to remote
```

---

## 📞 Support

- **Documentation**: See [docs/README.md](docs/README.md)
- **Issues**: Report bugs on GitHub
- **Examples**: See [examples/](examples/) directory
- **Tests**: See [tests/](tests/) directory

---

**Version**: 1.1.0  
**Last Updated**: December 22, 2025  
**Status**: Production Ready ✅

