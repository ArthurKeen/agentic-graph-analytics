# Analytics Catalog - Fraud Intelligence Setup Guide

**Date:** February 11, 2026

This document retraces the steps to configure and use the Analytics Catalog with the fraud-intelligence project.

---

## Step 1: Catalog Integration in agentic-graph-analytics

### ✅ Status: FULLY INTEGRATED

The Analytics Catalog is **fully integrated** into the agentic workflow in this project.

### Integration Points

| Component | Catalog Support | How |
|-----------|-----------------|-----|
| **AgenticWorkflowRunner** | ✅ | Accepts `catalog` parameter in constructor, passes to orchestrator |
| **OrchestratorAgent** | ✅ | Receives `catalog`, coordinates tracking across workflow |
| **RequirementsAgent** | ✅ | `catalog.track_requirements()` when catalog provided |
| **UseCaseAgent** | ✅ | `catalog.track_use_case()` when catalog provided |
| **TemplateAgent** | ✅ | `catalog.track_template()` when catalog provided |
| **ExecutionAgent** | ✅ | Creates `AnalysisExecutor(catalog=catalog)`, tracks executions |
| **AnalysisExecutor** | ✅ | `catalog.track_execution()` with optional `epoch_id` |

### Key Files

- `graph_analytics_ai/ai/agents/runner.py` - AgenticWorkflowRunner accepts `catalog`
- `graph_analytics_ai/ai/agents/orchestrator.py` - OrchestratorAgent receives catalog
- `graph_analytics_ai/ai/agents/specialized.py` - All agents (Requirements, UseCase, Template, Execution) accept `catalog`
- `graph_analytics_ai/ai/execution/executor.py` - AnalysisExecutor accepts `catalog` and `epoch_id`

---

## Step 2: Fraud-intelligence Configuration

### ✅ Status: PRE-CONFIGURED (with one fix needed)

The fraud-intelligence project at `~/code/fraud-intelligence` **already has catalog support** built into `run_fraud_analysis.py`.

### Current Configuration

1. **Environment** (`.env`):
   - `ARANGO_DATABASE` or `ARANGO_DB` → Must point to `fraud-intelligence` database
   - `FRAUD_ANALYSIS_ENABLE_CATALOG=true` (default)

2. **Env Mapping**:
   - fraud-intelligence uses `ARANGO_DB=fraud-intelligence` and `ARANGO_URL`
   - `_apply_env_mapping()` in run_fraud_analysis.py maps to platform's `ARANGO_ENDPOINT`, `ARANGO_DATABASE`

3. **Catalog Initialization**:
   - Creates `ArangoDBStorage(db)` → auto-creates collections on first use
   - Creates `AnalysisCatalog(storage)`
   - Creates/reuses epoch: `fraud-detection-YYYY-MM`

4. **Agent Wiring**:
   - Passes `catalog` to RequirementsAgent, UseCaseAgent, TemplateAgent, ExecutionAgent
   - Passes `catalog` to OrchestratorAgent

### Required Fix: Epoch Association for Executions

The ExecutionAgent's AnalysisExecutor needs `epoch_id` so that tracked executions are associated with the current epoch. Without this, executions are tracked but not linked to the epoch (so epoch-based queries return empty).

**Fix:**
```python
# After creating agents, set epoch on executor
if catalog and current_epoch:
    agents[AgentNames.EXECUTION_SPECIALIST].executor.epoch_id = current_epoch.epoch_id
```

---

## Step 3: Re-run Workflow to Populate Catalog

### Pre-requisites

1. **Database**: ArangoDB with `fraud-intelligence` database
2. **Graph**: Graph data loaded (e.g., KnowledgeGraph)
3. **Platform**: agentic-graph-analytics installed
   ```bash
   pip install -e ~/code/agentic-graph-analytics
   ```
4. **Environment**: `.env` in fraud-intelligence with:
   - `ARANGO_URL` or `ARANGO_ENDPOINT`
   - `ARANGO_USERNAME` or `ARANGO_USER`
   - `ARANGO_PASSWORD`
   - `ARANGO_DB=fraud-intelligence` or `ARANGO_DATABASE=fraud-intelligence`
   - LLM API keys (OpenRouter, etc.)
   - `FRAUD_ANALYSIS_ENABLE_CATALOG=true`

### Run Command

```bash
cd ~/code/fraud-intelligence
python run_fraud_analysis.py
```

### What Happens

1. **First run**: ArangoDBStorage creates catalog collections in `fraud-intelligence`:
   - `analysis_executions`
   - `analysis_epochs`
   - `analysis_requirements`
   - `analysis_use_cases`
   - `analysis_templates`
   - `analysis_lineage_edges`
   - `analysis_epoch_edges`

2. **Epoch**: Creates `fraud-detection-2026-02` (or current month)

3. **Workflow**: Runs agents, each tracking to catalog:
   - RequirementsAgent → requirements
   - UseCaseAgent → use cases
   - TemplateAgent → templates
   - ExecutionAgent → executions (with epoch_id after fix)

4. **Post-run**: Queries catalog to show tracked executions

### Verify Catalog Population

```python
from graph_analytics_ai.db_connection import get_db_connection
from graph_analytics_ai.catalog import AnalysisCatalog, CatalogQueries, ExecutionFilter
from graph_analytics_ai.catalog.storage import ArangoDBStorage

db = get_db_connection()
storage = ArangoDBStorage(db)
catalog = AnalysisCatalog(storage)

# List epochs
epochs = list(catalog.query_epochs(limit=10))
for e in epochs:
    print(f"Epoch: {e.name} (id={e.epoch_id})")

# Query executions
queries = CatalogQueries(storage)
executions = queries.query_with_pagination(
    filter=ExecutionFilter(status="completed"),
    page=1, page_size=50
)
print(f"Total executions: {executions.total_count}")
```

---

## Fixes Applied (February 11, 2026)

### 1. Model Adapters (agentic-graph-analytics)

The workflow produces types from `ai.documents`, `ai.generation`, and `ai.templates` that differ from catalog storage types. **Adapters** were added:

- `graph_analytics_ai/catalog/adapters.py` – converts workflow models to catalog models
- `track_requirements()`, `track_use_case()`, `track_template()` now accept both workflow and catalog types

### 2. Epoch Association (fraud-intelligence)

- `run_fraud_analysis.py` sets `executor.epoch_id = current_epoch.epoch_id` so executions are linked to the epoch

### 3. Environment Check

Ensure `ARANGO_ENDPOINT` includes the port, e.g. `https://host:8529` (not `https://host`).

---

## Summary

| Step | Status | Action |
|------|--------|--------|
| 1. Catalog in platform | ✅ Complete | Fully integrated |
| 2. Model adapters | ✅ Complete | Workflow types auto-converted |
| 3. fraud-intelligence config | ✅ Complete | epoch_id fix applied |
| 4. Run workflow | Ready | `cd fraud-intelligence && python run_fraud_analysis.py` |
