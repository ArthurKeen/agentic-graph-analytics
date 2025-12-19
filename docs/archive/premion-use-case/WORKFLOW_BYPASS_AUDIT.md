# Workflow Bypass Audit

**Date:** December 18, 2025  
**Issue:** Manual scripts bypassing the agentic workflow and available APIs

---

## ✅ PROPER AGENTIC WORKFLOW APIs

The project provides two approved workflow entry points:

### 1. **AgenticWorkflowRunner** (Autonomous Multi-Agent System)
- **Path:** `graph_analytics_ai.ai.agents.runner.AgenticWorkflowRunner`
- **Use case:** Full autonomous execution with AI agents
- **Example:** `run_full_agentic_workflow.py`

### 2. **WorkflowOrchestrator** (Step-by-Step Control)
- **Path:** `graph_analytics_ai.ai.workflow.orchestrator.WorkflowOrchestrator`
- **Use case:** Controlled execution with checkpointing
- **Example:** `run_agentic_workflow.py`, `run_premion_workflow.py`

### 3. **CLI Interface**
- **Command:** `gaai run-workflow`
- Wraps WorkflowOrchestrator for command-line use

---

## ❌ BYPASS SCRIPTS IDENTIFIED

### Critical Bypasses (Direct GAE/DB Access)

#### 1. `run_wcc_household_stitching.py`
- **Bypass:** Directly calls `get_gae_connection()` and manually executes WCC
- **Lines:** 39, 54, 163
- **Should use:** `AgenticWorkflowRunner` → `ExecutionAgent` → `TemplateAgent`
- **Impact:** Bypasses LLM-powered template generation, agent orchestration

#### 2. `generate_premion_templates.py`
- **Bypass:** Manually generates JSON templates with hardcoded algorithms
- **Lines:** 12-92 (PREMION_TEMPLATES dict)
- **Should use:** `TemplateAgent` via `AgenticWorkflowRunner`
- **Impact:** Bypasses LLM analysis, no schema awareness

#### 3. `execute_templates_properly.py`
- **Bypass:** Attempts manual template execution outside workflow
- **Lines:** 76-79 (direct AnalysisExecutor initialization)
- **Should use:** `AgenticWorkflowRunner.run()` or `WorkflowOrchestrator`
- **Impact:** Incomplete - recognizes bypass but doesn't fix it (see lines 102-107)

#### 4. `store_wcc_results.py`
- **Bypass:** Directly calls `get_gae_connection()` to store results
- **Lines:** 23, 38
- **Should use:** `ExecutionAgent` handles result storage automatically
- **Impact:** Manual result management bypasses workflow state tracking

#### 5. `create_result_collection.py`
- **Bypass:** Directly calls `get_db_connection()` to create collections
- **Lines:** 12, 37
- **Should use:** Database setup should be pre-workflow; agents handle results
- **Impact:** Manual collection management outside workflow

#### 6. `query_household_results.py`
- **Bypass:** Directly queries database for results
- **Lines:** 13, 43
- **Should use:** `ReportingAgent` generates insights from results
- **Impact:** Manual querying bypasses AI-powered reporting

### Debug/Inspection Scripts (Non-Production)

#### 7. `debug_job_status.py`
- **Purpose:** Debugging GAE job status format
- **Bypass:** Direct `get_gae_connection()` call (line 15)
- **Status:** Debug script, should be removed from production

#### 8. `debug_wcc_loading.py`
- **Purpose:** Debug graph loading behavior
- **Bypass:** Direct `get_gae_connection()` call (line 10)
- **Status:** Debug script, should be removed

#### 9. `inspect_premion_database.py`
- **Purpose:** Manual database inspection
- **Status:** Should use schema extraction via `SchemaAnalysisAgent`

#### 10. `inspect_premion_fixed.py`
- **Purpose:** Database inspection variant
- **Status:** Duplicate debug functionality

#### 11. `list_all_collections.py`
- **Purpose:** List database collections
- **Status:** Use `SchemaAnalysisAgent` instead

#### 12. `inspect_sharding.py`
- **Purpose:** Inspect sharding configuration
- **Status:** Manual inspection, should use schema analysis

#### 13. `test_premion_connection.py`
- **Purpose:** Connection testing
- **Status:** Valid for setup, but not workflow

### Manual Template Directory

#### 14. `premion_gae_templates/`
- **Contents:** Manually created JSON templates + execution script
- **Bypass:** Entire directory bypasses `TemplateAgent` LLM generation
- **Files:**
  - `household_identity_resolution.json`
  - `commercial_ip_filtering.json`
  - `cross_device_attribution.json`
  - `audience_propagation.json`
  - `inventory_influence.json`
  - `execute_templates.py`
  - `manifest.json`

---

## 📊 BYPASS SUMMARY

| Category | Count | Action |
|----------|-------|--------|
| **Critical Bypasses** | 6 | Refactor or delete |
| **Debug Scripts** | 7 | Delete |
| **Manual Templates** | 1 dir (7 files) | Delete |
| **TOTAL** | 14 files/dirs | Clean up |

---

## ✅ APPROVED SCRIPTS (Keep These)

### Production Scripts
- ✅ `run_full_agentic_workflow.py` - Uses `AgenticWorkflowRunner` (CORRECT)
- ✅ `run_agentic_workflow.py` - Uses `WorkflowOrchestrator` (CORRECT)
- ✅ `run_premion_workflow.py` - Uses `WorkflowOrchestrator` (CORRECT)
- ✅ `view_agentic_results.py` - Results viewer (utility)

### Example Scripts
- ✅ `examples/agentic_workflow_example.py` - Demonstrates proper API usage
- ✅ `examples/agentic_workflow_demo.py` - Educational demo
- ✅ `examples/validate_workflows.py` - Compares both workflows

---

## 🔧 RECOMMENDED ACTIONS

### 1. Delete All Bypass Scripts
```bash
# Critical bypasses
rm run_wcc_household_stitching.py
rm generate_premion_templates.py
rm execute_templates_properly.py
rm store_wcc_results.py
rm create_result_collection.py
rm query_household_results.py

# Debug scripts
rm debug_job_status.py
rm debug_wcc_loading.py
rm inspect_premion_database.py
rm inspect_premion_fixed.py
rm list_all_collections.py
rm inspect_sharding.py
rm test_premion_connection.py

# Manual templates
rm -rf premion_gae_templates/
```

### 2. Consolidate Duplicate Workflow Scripts

Currently have 3 scripts doing similar things:
- `run_full_agentic_workflow.py` (AgenticWorkflowRunner)
- `run_agentic_workflow.py` (WorkflowOrchestrator)
- `run_premion_workflow.py` (WorkflowOrchestrator)

**Recommendation:** Keep `run_full_agentic_workflow.py` as the primary example, move others to `examples/`

### 3. Update Documentation

Remove references to manual scripts in:
- `CLEANUP_RECOMMENDATIONS.md`
- `LIBRARY_ARCHITECTURE_SUMMARY.md`

---

## 💡 CORRECT USAGE PATTERNS

### For Premion Use Case (CORRECT)

```python
#!/usr/bin/env python3
from graph_analytics_ai.ai.agents.runner import AgenticWorkflowRunner
from graph_analytics_ai.db_connection import get_db_connection

# ✅ CORRECT: Use AgenticWorkflowRunner
runner = AgenticWorkflowRunner(
    db_connection=get_db_connection(),
    graph_name="PremionIdentityGraph"
)

# Run complete workflow - agents handle everything
final_state = runner.run(
    input_documents=[{
        "path": "consumer_media_use_cases.md",
        "content": doc_content,
        "type": "text/markdown"
    }],
    max_executions=3
)

# Access results
for report in final_state.reports:
    print(report.title)
```

### What NOT To Do (INCORRECT)

```python
# ❌ INCORRECT: Direct GAE access
from graph_analytics_ai.gae_connection import get_gae_connection
gae = get_gae_connection()
gae.run_wcc(graph_id)  # Bypasses workflow!

# ❌ INCORRECT: Manual template generation
templates = [{"algorithm": "wcc", ...}]  # Bypasses LLM!

# ❌ INCORRECT: Direct database queries for results
db.aql.execute("FOR doc IN results...")  # Bypasses reporting!
```

---

## 🎯 CONCLUSION

**Total files to remove:** 14 (13 scripts + 1 directory)

All functionality is available through:
1. `AgenticWorkflowRunner` - For autonomous execution
2. `WorkflowOrchestrator` - For controlled execution
3. Individual agents - For custom workflows

**No manual scripts or templates are needed.**

---

_Audit completed: December 18, 2025_


