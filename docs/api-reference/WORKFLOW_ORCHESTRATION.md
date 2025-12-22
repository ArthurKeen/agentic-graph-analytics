
# Workflow Orchestration Guide

**Phase 6: Complete Workflow Automation**

This guide explains how to use the AI-assisted workflow orchestration system to automate your graph analytics from business requirements to actionable insights.

## Overview

The workflow orchestration system provides end-to-end automation of the AI-assisted graph analytics process. It coordinates all components (LLM, schema analysis, document processing, PRD generation, use case generation) into a seamless workflow.

### Key Features

- **Complete Automation**: From requirements to insights with minimal manual intervention
- **State Management**: Track progress through all workflow steps
- **Checkpointing**: Save and resume workflows at any point
- **Error Handling**: Automatic retry logic with graceful degradation
- **CLI Interface**: Easy command-line access to all functionality
- **Flexible Execution**: Run complete workflow or individual steps

## Architecture

### Workflow Steps

The workflow consists of 7 main steps:

1. **Parse Documents** - Parse business requirement documents (PDF, DOCX, TXT, MD, HTML)
2. **Extract Requirements** - Extract structured requirements using LLM
3. **Extract Schema** - Extract graph schema from ArangoDB
4. **Analyze Schema** - Analyze schema structure with LLM insights
5. **Generate PRD** - Create Product Requirements Document
6. **Generate Use Cases** - Create graph analytics use cases
7. **Save Outputs** - Save all artifacts to files

### Components

```
┌─────────────────────────────────────────────────────────┐
│           WorkflowOrchestrator (orchestrator.py)        │
│  • Coordinates step execution                           │
│  • Manages state and checkpoints                        │
│  • Handles errors and retries                           │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌───────────────┐  ┌────────────┐  ┌──────────────┐
│ WorkflowState │  │WorkflowSteps│  │ Exceptions   │
│  (state.py)   │  │ (steps.py)  │  │(exceptions.py)│
│               │  │             │  │              │
│ • Status      │  │ • Execute   │  │ • Error types│
│ • Progress    │  │   each step │  │ • Messages   │
│ • Checkpoint  │  │ • Format    │  │              │
└───────────────┘  └────────────┘  └──────────────┘
```

## Installation

```bash
# Install with CLI support
pip install -e .

# Or with click directly
pip install click>=8.0.0

# Verify installation
gaai version
```

## Quick Start

### Using CLI (Recommended)

The easiest way to use the workflow is through the CLI:

```bash
gaai run-workflow \
  --requirements requirements.pdf \
  --database-endpoint http://localhost:8529 \
  --database-name my_graph \
  --database-password password \
  --output-dir ./output
```

### Using Python API

For programmatic access:

```python
from graph_analytics_ai.ai.workflow import WorkflowOrchestrator

# Create orchestrator
orchestrator = WorkflowOrchestrator(
    output_dir="./workflow_output",
    enable_checkpoints=True,
    max_retries=3
)

# Run complete workflow
result = orchestrator.run_complete_workflow(
    business_requirements=["requirements.pdf", "scope.docx"],
    database_endpoint="http://localhost:8529",
    database_name="my_graph",
    database_password="password",
    product_name="My Analytics Project"
)

# Check results
if result.status == WorkflowStatus.COMPLETED:
    print(f"PRD: {result.prd_path}")
    print(f"Use Cases: {result.use_cases_path}")
    print(f"Completed in {result.total_duration_seconds:.2f}s")
else:
    print(f"Failed: {result.error_message}")
```

## CLI Commands

### run-workflow

Run the complete end-to-end workflow.

```bash
gaai run-workflow [OPTIONS]

Options:
  -r, --requirements PATH      Business requirements document (can be specified multiple times)
  -e, --database-endpoint URL  ArangoDB endpoint (e.g., http://localhost:8529)
  -d, --database-name NAME     Database name to analyze
  -u, --database-username NAME Database username (default: root)
  -p, --database-password TEXT Database password
  --product-name TEXT          Product/project name for PRD
  -o, --output-dir PATH        Output directory (default: ./workflow_output)
  --resume                     Resume from last checkpoint
  --no-checkpoints             Disable checkpoint saving
```

**Example:**

```bash
gaai run-workflow \
  -r requirements.pdf \
  -r business_case.docx \
  -e http://localhost:8529 \
  -d ecommerce_graph \
  -p my_password \
  --product-name "E-commerce Analytics" \
  -o ./ecommerce_output
```

### analyze-schema

Analyze graph database schema only.

```bash
gaai analyze-schema [OPTIONS]

Options:
  -e, --database-endpoint URL  ArangoDB endpoint
  -d, --database-name NAME     Database name
  -u, --database-username NAME Database username
  -p, --database-password TEXT Database password
  -o, --output PATH            Output file for report (optional)
```

**Example:**

```bash
gaai analyze-schema \
  -e http://localhost:8529 \
  -d my_graph \
  -p password \
  -o schema_report.md
```

### parse-requirements

Parse and extract requirements from documents.

```bash
gaai parse-requirements DOCUMENTS... [OPTIONS]

Options:
  -o, --output PATH  Output file for requirements summary

Arguments:
  DOCUMENTS  One or more document paths
```

**Example:**

```bash
gaai parse-requirements \
  requirements.pdf \
  scope.docx \
  notes.txt \
  -o requirements_summary.md
```

### status

Check workflow execution status and progress.

```bash
gaai status [OPTIONS]

Options:
  -o, --output-dir PATH  Workflow output directory (default: ./workflow_output)
```

**Example:**

```bash
gaai status -o ./my_workflow_output
```

### version

Show version and feature information.

```bash
gaai version
```

## State Management

### Workflow States

The workflow can be in one of these states:

- `NOT_STARTED` - Workflow has not begun
- `IN_PROGRESS` - Currently executing
- `COMPLETED` - Successfully finished
- `FAILED` - Execution failed
- `PAUSED` - Temporarily paused

### Checkpointing

Checkpoints are automatically saved after each step (unless disabled):

```python
# Enable checkpointing (default)
orchestrator = WorkflowOrchestrator(
    output_dir="./output",
    enable_checkpoints=True
)

# Resume from checkpoint
result = orchestrator.run_complete_workflow(
    ...,
    resume_from_checkpoint=True
)
```

Checkpoint files are saved as `checkpoint_<workflow_id>.json` in the output directory.

### Progress Tracking

Get real-time progress information:

```python
progress = orchestrator.get_progress()

print(f"Status: {progress['status']}")
print(f"Progress: {progress['progress'] * 100:.1f}%")
print(f"Completed: {progress['completed_steps']}/{progress['total_steps']}")
print(f"Current Step: {progress['current_step']}")
```

## Error Handling

### Automatic Retries

Failed steps are automatically retried:

```python
orchestrator = WorkflowOrchestrator(
    max_retries=3  # Retry up to 3 times per step
)
```

### Error Recovery

When a step fails:

1. Error is logged to the state
2. Step is retried (up to `max_retries`)
3. If all retries fail, workflow marks as FAILED
4. State is saved to checkpoint
5. Workflow can be resumed later

### Handling Failures

```python
result = orchestrator.run_complete_workflow(...)

if result.status == WorkflowStatus.FAILED:
    print(f"Error: {result.error_message}")
    print(f"Completed steps: {', '.join(result.completed_steps)}")
    
    # Review checkpoint for details
    state = orchestrator.get_state()
    for step_name, step_result in state.step_results.items():
        if step_result.status == WorkflowStatus.FAILED:
            print(f"Failed step: {step_name}")
            print(f"Error: {step_result.error_message}")
```

## Configuration

### Environment Variables

Configure LLM and other settings via environment variables:

```bash
# LLM Configuration
export OPENROUTER_API_KEY="your-key-here"
export OPENROUTER_MODEL="anthropic/claude-3.5-sonnet"

# Or use .env file
cat > .env << EOF
OPENROUTER_API_KEY=your-key-here
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
EOF
```

### Custom LLM Provider

Use a custom LLM provider:

```python
from graph_analytics_ai.ai.llm import create_llm_provider

# Create custom provider
llm_provider = create_llm_provider(
    provider_type="openrouter",
    api_key="your-key",
    model="anthropic/claude-3.5-sonnet"
)

# Use with orchestrator
orchestrator = WorkflowOrchestrator(
    llm_provider=llm_provider
)
```

## Output Files

After successful execution, the following files are created:

### product_requirements.md

Complete Product Requirements Document with:
- Overview and domain information
- Objectives and success criteria
- Detailed requirements (functional, non-functional, technical)
- Stakeholder information
- Schema summary (if analyzed)
- Constraints and risks

### use_cases.md

Graph analytics use cases with:
- Use case ID and title
- Type (centrality, community, pathfinding, etc.)
- Priority level
- Detailed description
- Related requirements
- Suggested algorithms
- Data requirements
- Expected outputs
- Success metrics

### schema_analysis.md

Schema analysis report with:
- Database statistics
- Collection breakdown
- Relationship mapping
- LLM insights (domain identification, complexity, recommendations)

### requirements_summary.md

Requirements extraction summary with:
- Domain and executive summary
- Objectives grouped by priority
- Requirements grouped by priority
- Stakeholder information

## Advanced Usage

### Partial Workflow Execution

Execute only specific steps (coming soon):

```python
result = orchestrator.run_partial_workflow(
    steps_to_run=[
        WorkflowStep.EXTRACT_SCHEMA,
        WorkflowStep.ANALYZE_SCHEMA
    ],
    database_endpoint="...",
    database_name="..."
)
```

### Custom Step Execution

Execute individual steps directly:

```python
from graph_analytics_ai.ai.workflow import WorkflowSteps
from graph_analytics_ai.ai.llm import create_llm_provider

provider = create_llm_provider()
steps = WorkflowSteps(provider)

# Extract schema
schema = steps.extract_schema(
    database_endpoint="http://localhost:8529",
    database_name="my_graph",
    password="password"
)

# Analyze schema
analysis = steps.analyze_schema(schema)

# Generate report
from graph_analytics_ai.ai.schema import SchemaAnalyzer
analyzer = SchemaAnalyzer(provider)
report = analyzer.generate_report(analysis)
```

### Integration with Existing Code

Integrate workflow into existing applications:

```python
from graph_analytics_ai.ai.workflow import WorkflowOrchestrator

class MyAnalyticsPipeline:
    def __init__(self):
        self.orchestrator = WorkflowOrchestrator()
    
    def run_analysis(self, requirements_path, database_config):
        result = self.orchestrator.run_complete_workflow(
            business_requirements=[requirements_path],
            **database_config
        )
        
        if result.status == WorkflowStatus.COMPLETED:
            self.process_results(result)
        else:
            self.handle_error(result)
    
    def process_results(self, result):
        # Load and process generated artifacts
        prd_content = Path(result.prd_path).read_text()
        # ... process PRD, use cases, etc.
```

## Best Practices

### 1. Use Checkpointing

Always enable checkpointing for long-running workflows:

```python
orchestrator = WorkflowOrchestrator(
    enable_checkpoints=True  # Default
)
```

### 2. Monitor Progress

For long workflows, monitor progress:

```python
import time
from threading import Thread

def monitor_progress(orchestrator):
    while orchestrator.state and orchestrator.state.status == WorkflowStatus.IN_PROGRESS:
        progress = orchestrator.get_progress()
        print(f"Progress: {progress['progress'] * 100:.1f}%")
        time.sleep(5)

# Start monitoring in background
Thread(target=monitor_progress, args=(orchestrator,), daemon=True).start()

# Run workflow
result = orchestrator.run_complete_workflow(...)
```

### 3. Validate Inputs

Validate inputs before running workflow:

```python
from pathlib import Path

# Check requirements files exist
requirements = ["req1.pdf", "req2.docx"]
for req_path in requirements:
    if not Path(req_path).exists():
        raise FileNotFoundError(f"Requirements file not found: {req_path}")

# Test database connection
from graph_analytics_ai.db_connection import get_db_connection
try:
    db = get_db_connection(
        endpoint=database_endpoint,
        database=database_name,
        password=database_password
    )
    db.aql.execute("RETURN 1")
except Exception as e:
    raise ConnectionError(f"Cannot connect to database: {e}")
```

### 4. Handle Failures Gracefully

Implement proper error handling:

```python
try:
    result = orchestrator.run_complete_workflow(...)
    
    if result.status == WorkflowStatus.FAILED:
        # Log error
        logger.error(f"Workflow failed: {result.error_message}")
        
        # Notify stakeholders
        send_notification(
            subject="Workflow Failed",
            body=f"Error: {result.error_message}\n"
                 f"Completed: {len(result.completed_steps)} steps"
        )
        
        # Optionally retry
        if is_retryable_error(result.error_message):
            result = orchestrator.run_complete_workflow(
                ...,
                resume_from_checkpoint=True
            )
except Exception as e:
    logger.exception("Unexpected error in workflow")
    raise
```

## Troubleshooting

### Workflow Stuck or Slow

- Check LLM API rate limits
- Verify database connectivity
- Review checkpoint file for progress
- Check system resources (memory, CPU)

### Step Failures

Common issues and solutions:

**Parse Documents Failed:**
- Ensure files exist and are readable
- Check file format is supported
- Verify sufficient disk space

**Extract Requirements Failed:**
- Check LLM API key and connectivity
- Verify sufficient API credits
- Review document content quality

**Extract Schema Failed:**
- Verify database connection settings
- Check user permissions on database
- Ensure database is accessible

**Analyze Schema Failed:**
- Check LLM API availability
- Verify schema extraction succeeded
- Review complexity of schema

### Checkpoint Issues

If checkpoints are corrupted:

```bash
# Remove corrupted checkpoints
rm ./workflow_output/checkpoint_*.json

# Restart workflow
gaai run-workflow ...
```

## Performance Tips

1. **Use Batch Processing**: Process multiple requirements files together
2. **Optimize Retries**: Set `max_retries` appropriately based on reliability
3. **Disable Checkpoints**: For short workflows, disable to improve speed
4. **Choose Right LLM**: Balance cost vs. quality based on use case
5. **Parallel Execution**: Run independent steps in parallel (future enhancement)

## Examples

See [examples/workflow_examples.py](../examples/workflow_examples.py) for:
- Complete workflow execution
- Error handling patterns
- Resume from checkpoint
- Custom step execution
- Integration examples

## API Reference

### WorkflowOrchestrator

Main orchestrator class.

**Methods:**
- `run_complete_workflow()` - Execute complete workflow
- `get_progress()` - Get current progress
- `get_state()` - Get workflow state

### WorkflowState

Workflow state management.

**Methods:**
- `mark_step_started()` - Mark step as started
- `mark_step_completed()` - Mark step as completed
- `mark_step_failed()` - Mark step as failed
- `save_checkpoint()` - Save to checkpoint file
- `load_checkpoint()` - Load from checkpoint file

### WorkflowSteps

Individual step executors.

**Methods:**
- `parse_documents()` - Parse requirement documents
- `extract_requirements()` - Extract requirements with LLM
- `extract_schema()` - Extract graph schema
- `analyze_schema()` - Analyze schema with LLM
- `generate_prd()` - Generate PRD document
- `generate_use_cases()` - Generate use cases
- `save_outputs()` - Save all outputs

## Next Steps

- **Phase 7**: Agentic workflow with autonomous agents
- **CLI Enhancements**: Interactive mode, progress bars
- **Parallel Execution**: Run independent steps concurrently
- **Web Interface**: Browser-based workflow management
- **Monitoring**: Real-time metrics and dashboards

## Support

For issues or questions:
- GitHub Issues: https://github.com/ArthurKeen/graph-analytics-ai/issues
- Documentation: https://github.com/ArthurKeen/graph-analytics-ai/docs

