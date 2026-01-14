# Environment Variables for Graph Analytics AI Platform

This file documents all environment variables that can be used to configure the platform.

## Database Configuration

```bash
# ArangoDB connection
ARANGO_HOST=localhost
ARANGO_PORT=8529
ARANGO_USERNAME=root
ARANGO_PASSWORD=your_password
ARANGO_DATABASE=_system
```

## LLM Configuration

```bash
# OpenRouter API configuration
OPENROUTER_API_KEY=your_api_key_here
LLM_MODEL=anthropic/claude-3.5-sonnet

# LLM Provider settings
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4000
```

## GAE Engine Management

These settings control how Graph Analytics Engines are managed and cleaned up.

```bash
# Automatically cleanup engines after workflow completion (default: true)
# Set to "false" to leave engines running for inspection/debugging
GAE_AUTO_CLEANUP=true

# Automatically cleanup existing engines before starting new ones (default: true)
# Set to "false" to fail fast if engines are already running (prevents accidental double billing)
GAE_AUTO_CLEANUP_EXISTING=true
```

**Important Notes**:
- **`GAE_AUTO_CLEANUP=true`** (Recommended): Engines are deleted after each workflow, preventing ongoing charges
- **`GAE_AUTO_CLEANUP_EXISTING=true`** (Recommended): If previous runs failed and left engines running, they'll be cleaned up automatically
- **Cost Impact**: Leaving engines running (`GAE_AUTO_CLEANUP=false`) will continue to incur hourly charges
- **Debugging**: Set both to `false` only when you need to inspect engine state after execution

## Reporting Agent Configuration

These settings control LLM-based insight generation for reports.

```bash
# Enable or disable LLM interpretation in reports (default: true)
# Set to "false" to use only heuristic insights (faster, cheaper)
GAE_PLATFORM_USE_LLM_REPORTING=true

# Minimum confidence threshold for insights (default: 0.5)
# Insights below this threshold will be filtered out
# Range: 0.0 to 1.0
GAE_PLATFORM_REPORTING_MIN_CONFIDENCE=0.5

# Enable chain-of-thought reasoning for insight generation (default: false)
# This improves quality but increases LLM costs and latency
GAE_PLATFORM_REPORTING_USE_REASONING=false

# Maximum number of LLM insights per report (default: 5)
# Limits the number of insights to control cost and report length
GAE_PLATFORM_MAX_LLM_INSIGHTS_PER_REPORT=5

# Timeout for LLM calls in seconds (default: 30)
# If LLM doesn't respond within this time, falls back to heuristics
GAE_PLATFORM_LLM_REPORTING_TIMEOUT=30
```

## Cost Optimization Tips

### High Quality (Higher Cost)
```bash
GAE_PLATFORM_USE_LLM_REPORTING=true
GAE_PLATFORM_REPORTING_USE_REASONING=true
GAE_PLATFORM_REPORTING_MIN_CONFIDENCE=0.7
GAE_PLATFORM_MAX_LLM_INSIGHTS_PER_REPORT=6
```

### Balanced (Recommended)
```bash
GAE_PLATFORM_USE_LLM_REPORTING=true
GAE_PLATFORM_REPORTING_USE_REASONING=false
GAE_PLATFORM_REPORTING_MIN_CONFIDENCE=0.5
GAE_PLATFORM_MAX_LLM_INSIGHTS_PER_REPORT=5
```

### Fast & Cost-Effective
```bash
GAE_PLATFORM_USE_LLM_REPORTING=false
# When LLM is disabled, other settings are ignored
# Reports will use improved heuristic insights
```

## Workflow Configuration

```bash
# Output directory for workflow artifacts
WORKFLOW_OUTPUT_DIR=./workflow_output

# Enable verbose logging
WORKFLOW_VERBOSE=true
```

## Example .env File

Create a `.env` file in the project root with your configuration:

```bash
# Database
ARANGO_HOST=localhost
ARANGO_PORT=8529
ARANGO_USERNAME=root
ARANGO_PASSWORD=your_secure_password
ARANGO_DATABASE=graph_analytics

# LLM
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
LLM_MODEL=anthropic/claude-3.5-sonnet

# Reporting (use defaults or customize)
GAE_PLATFORM_USE_LLM_REPORTING=true
GAE_PLATFORM_REPORTING_MIN_CONFIDENCE=0.5
GAE_PLATFORM_REPORTING_USE_REASONING=false
GAE_PLATFORM_MAX_LLM_INSIGHTS_PER_REPORT=5
GAE_PLATFORM_LLM_REPORTING_TIMEOUT=30
```

## Loading Environment Variables

The platform automatically loads environment variables from:
1. System environment variables
2. `.env` file in the project root (using python-dotenv)

To use a custom .env file location:
```python
from dotenv import load_dotenv
load_dotenv('/path/to/your/.env')
```
