# Environment Variable Clarification

## ❌ ENABLE_RETRY is NOT an Environment Variable

**Issue:** Some documentation examples incorrectly included `ENABLE_RETRY=true` in .env files.

**Fact:** `ENABLE_RETRY` is **NOT** a recognized environment variable in the graph-analytics-ai library.

---

## ✅ How Retry Actually Works

Retry functionality is controlled through **code parameters**, not environment variables.

### WorkflowOrchestrator (Traditional Workflow)

```python
from graph_analytics_ai.ai.workflow.orchestrator import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator(
    output_dir="./workflow_output",
    enable_checkpoints=True,
    max_retries=3  # ← Configured here, not in .env
)
```

**Parameters:**
- `max_retries` (int) - Maximum number of retries for failed steps (default: 3)
- `enable_checkpoints` (bool) - Whether to save checkpoints (default: True)

### AgenticWorkflowRunner (Agentic Workflow)

Retry is built into the agents - they have their own retry logic defined in code:

```python
from graph_analytics_ai.ai.agents.runner import AgenticWorkflowRunner

runner = AgenticWorkflowRunner(
    db_connection=get_db_connection(),
    graph_name="MyGraph"
)
# Agents have built-in retry logic (MAX_RETRIES = 2)
```

The retry constants are defined in the agent code, not in environment variables.

---

## Valid Environment Variables

Here are the **actual** environment variables supported by the library:

### Database Configuration
- ✅ `ARANGO_ENDPOINT` - Database endpoint URL
- ✅ `ARANGO_DATABASE` - Database name
- ✅ `ARANGO_USER` - Username (default: root)
- ✅ `ARANGO_PASSWORD` - Password
- ✅ `ARANGO_VERIFY_SSL` - SSL verification (true/false)
- ✅ `ARANGO_TIMEOUT` - Connection timeout in seconds

### GAE Configuration
- ✅ `GAE_DEPLOYMENT_MODE` - Deployment mode (amp/self_managed)
- ✅ `ARANGO_GRAPH_API_KEY_ID` - API key ID (for AMP)
- ✅ `ARANGO_GRAPH_API_KEY_SECRET` - API key secret (for AMP)
- ✅ `ARANGO_GAE_PORT` - GAE port (default: 8829)

### LLM Configuration
- ✅ `LLM_PROVIDER` - Provider name (openrouter/openai/anthropic/gemini)
- ✅ `OPENROUTER_API_KEY` - OpenRouter API key
- ✅ `OPENROUTER_MODEL` - OpenRouter model name
- ✅ `OPENAI_API_KEY` - OpenAI API key (if using openai)
- ✅ `OPENAI_MODEL` - OpenAI model name (if using openai)
- ✅ `ANTHROPIC_API_KEY` - Anthropic API key (if using anthropic)
- ✅ `ANTHROPIC_MODEL` - Anthropic model name (if using anthropic)
- ✅ `GOOGLE_API_KEY` - Google API key (if using gemini)
- ✅ `GEMINI_MODEL` - Gemini model name (if using gemini)
- ✅ `LLM_MAX_RETRIES` - Max retries for LLM calls (default: 3)

### Optional General Settings
- ✅ `LOG_LEVEL` - Logging level (DEBUG/INFO/WARNING/ERROR)
- ✅ `ENVIRONMENT` - Environment name (production/development/test)

### NOT Valid (Custom/App-Level Only)
- ❌ `ENABLE_RETRY` - Not recognized by library
- ❌ `MAX_EXECUTIONS` - Not recognized by library (use in code)
- ❌ `CHECKPOINT_DIR` - Not recognized by library (use in code)
- ❌ `REPORTS_DIR` - Not recognized by library (use in code)
- ❌ `STATE_DIR` - Not recognized by library (use in code)
- ❌ `GRAPH_NAME` - Not recognized by library (use in code)

---

## Corrected .env Files

### Library Project (.env)
```bash
# Database
ARANGO_DATABASE=graph-analytics-ai
ARANGO_USER=root
ARANGO_PASSWORD=your_test_password
ARANGO_ENDPOINT=https://your-test-cluster.arangodb.cloud:8529
ARANGO_VERIFY_SSL=true
ARANGO_TIMEOUT=30

# GAE
GAE_DEPLOYMENT_MODE=amp
ARANGO_GRAPH_API_KEY_ID=your_test_api_key_id
ARANGO_GRAPH_API_KEY_SECRET=your_test_api_key_secret

# LLM
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=google/gemini-flash-1.5-8b

# Optional
LOG_LEVEL=INFO
```

### Customer Project (.env)
```bash
# Database
ARANGO_DATABASE=your_production_database
ARANGO_USER=root
ARANGO_PASSWORD=your_production_password
ARANGO_ENDPOINT=https://your-production-cluster.arangodb.cloud:8529
ARANGO_VERIFY_SSL=true
ARANGO_TIMEOUT=30

# GAE
GAE_DEPLOYMENT_MODE=amp
ARANGO_GRAPH_API_KEY_ID=your_production_api_key_id
ARANGO_GRAPH_API_KEY_SECRET=your_production_api_key_secret

# LLM
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=google/gemini-flash-1.5-8b

# Optional
LOG_LEVEL=INFO

# Custom app-level vars (not used by library, but useful for your scripts)
GRAPH_NAME=YourGraphName
MAX_EXECUTIONS=3
CHECKPOINT_DIR=./outputs/checkpoints
REPORTS_DIR=./outputs/generated_reports
STATE_DIR=./outputs
```

---

## How to Configure Retry

### In Traditional Workflow

```python
from graph_analytics_ai.ai.workflow.orchestrator import WorkflowOrchestrator

# Configure retry when creating orchestrator
orchestrator = WorkflowOrchestrator(
    output_dir="./workflow_output",
    enable_checkpoints=True,
    max_retries=5  # Set your desired retry count
)

result = orchestrator.run_complete_workflow(
    business_requirements=["requirements.md"],
    database_endpoint=os.getenv("ARANGO_ENDPOINT"),
    database_name=os.getenv("ARANGO_DATABASE"),
    database_username=os.getenv("ARANGO_USER"),
    database_password=os.getenv("ARANGO_PASSWORD")
)
```

### In Agentic Workflow

Retry is built-in and automatic. Agents have pre-configured retry logic:

```python
from graph_analytics_ai.ai.agents.runner import AgenticWorkflowRunner

runner = AgenticWorkflowRunner(
    db_connection=get_db_connection(),
    graph_name="MyGraph"
)

# Agents handle retry automatically
state = runner.run()
```

If you need custom retry behavior, you'd need to configure the individual agents when creating them.

---

## Summary

✅ **Removed:** `ENABLE_RETRY=true` from all .env examples  
✅ **Reason:** Not a recognized environment variable  
✅ **Solution:** Configure retry through code parameters  
✅ **Updated:** All documentation to reflect actual configuration options  

---

**Key Takeaway:** Only variables that the library reads from environment (in `config.py` and LLM factory) should be in .env files. Application-level settings like `GRAPH_NAME`, `MAX_EXECUTIONS`, etc. are fine to include for your own scripts, but the library won't read them.

