# Backward Compatibility Architecture

## Module Structure - Before and After

### Current Structure (v1.2.0)
```
graph_analytics_ai/
├── __init__.py              ← Public API
├── config.py
├── db_connection.py
├── gae_connection.py
├── gae_orchestrator.py
├── results.py
├── queries.py
├── export.py
└── utils.py
```

### With AI Features (v2.0.0+)
```
graph_analytics_ai/
├── __init__.py              ← UNCHANGED - Same public API
├── config.py                ← Extended with AI config (optional)
├── db_connection.py         ← UNCHANGED
├── gae_connection.py        ← UNCHANGED
├── gae_orchestrator.py      ← UNCHANGED
├── results.py               ← UNCHANGED
├── queries.py               ← UNCHANGED
├── export.py                ← UNCHANGED
├── utils.py                 ← UNCHANGED
└── ai/                      ← NEW - Completely separate module
    ├── __init__.py          ← AI public API
    ├── config.py
    ├── workflow.py
    ├── llm/
    ├── agents/
    ├── schema/
    ├── generation/
    ├── execution/
    └── reporting/
```

## Import Compatibility

### Existing Code (Continues to Work)
```python
# All existing imports work exactly as before
from graph_analytics_ai import (
    GAEOrchestrator,
    AnalysisConfig,
    AnalysisResult,
    AnalysisStatus,
    get_arango_config,
    get_gae_config,
    get_db_connection
)

# Usage unchanged
orchestrator = GAEOrchestrator()
result = orchestrator.run_analysis(config)
```

### New AI Features (Opt-In)
```python
# New imports for AI features (optional)
from graph_analytics_ai.ai import (
    AIWorkflowOrchestrator,
    LLMProvider,
    SchemaAnalyzer
)

# Existing imports still available
from graph_analytics_ai import GAEOrchestrator, AnalysisConfig
```

## Dependency Compatibility

### Core Dependencies (Required - Unchanged)
```txt
python-arango>=7.0.0
requests>=2.28.0
python-dotenv>=0.19.0
```

### AI Dependencies (Optional - New)
```txt
# Install only if using AI features:
# pip install graph-analytics-ai[ai]

litellm>=1.0.0
pydantic>=2.0.0
```

## Configuration Compatibility

### Existing Configuration (Required)
```bash
# .env - These remain required for all users
ARANGO_ENDPOINT=https://...
ARANGO_USER=root
ARANGO_PASSWORD=...
ARANGO_DATABASE=...
GAE_DEPLOYMENT_MODE=amp
```

### AI Configuration (Optional - New)
```bash
# .env - Only needed if using AI features
AI_WORKFLOW_ENABLED=true        # Must explicitly enable
OPENROUTER_API_KEY=sk-or-v1-... # Customer provides
OPENROUTER_MODEL=google/gemini-2.5-flash
LLM_PROVIDER=openrouter
```

## Code Path Comparison

### Path 1: Existing Workflow (Unchanged)
```
Customer Code
    ↓
GAEOrchestrator (existing)
    ↓
GAEConnection (existing)
    ↓
ArangoDB + GAE
    ↓
AnalysisResult (existing)
```

### Path 2: AI-Assisted Workflow (New, Optional)
```
Customer Documents
    ↓
AIWorkflowOrchestrator (new)
    ↓
LLM Provider (new)
    ↓
Generate AnalysisConfig (new)
    ↓
GAEOrchestrator (REUSES EXISTING)
    ↓
GAEConnection (REUSES EXISTING)
    ↓
ArangoDB + GAE
    ↓
AnalysisResult (existing)
    ↓
Report Generator (new)
```

**Key Point:** Both paths use the same core orchestration infrastructure!

## Runtime Behavior

### Existing Code Behavior
```python
# File: customer_code.py
from graph_analytics_ai import GAEOrchestrator, AnalysisConfig

# This code:
# ✅ Works exactly as before
# ✅ No performance impact
# ✅ No new dependencies loaded
# ✅ No AI features activated
# ✅ Same behavior, same results

orchestrator = GAEOrchestrator()
result = orchestrator.run_analysis(config)
```

### AI Features Behavior
```python
# File: customer_ai_code.py
from graph_analytics_ai.ai import AIWorkflowOrchestrator

# This code:
# ✅ Only loads AI modules when imported
# ✅ Only activates if AI_WORKFLOW_ENABLED=true
# ✅ Only uses LLM if customer provides key
# ✅ Falls back gracefully if AI unavailable
# ✅ Can mix with existing GAEOrchestrator

workflow = AIWorkflowOrchestrator()
result = workflow.run_complete_workflow(...)
```

## Test Compatibility

### Existing Tests (Must Pass)
```python
# test_gae_orchestrator.py - UNCHANGED
def test_basic_analysis():
    """Existing test continues to pass."""
    config = AnalysisConfig(...)
    orchestrator = GAEOrchestrator()
    result = orchestrator.run_analysis(config)
    assert result.status == AnalysisStatus.SUCCESS
```

### New AI Tests (Separate)
```python
# test_ai_workflow.py - NEW
def test_ai_workflow():
    """New test for AI features."""
    workflow = AIWorkflowOrchestrator(...)
    result = workflow.run_complete_workflow(...)
    assert result.report is not None
```

## Migration Path for Projects

### Project 1: dnb_er (No Changes Needed)
```python
# Current code - continues working
from graph_analytics_ai import GAEOrchestrator, AnalysisConfig

# No changes required
# No new dependencies needed
# No configuration changes needed
```

### Project 2: matpriskollen (Optional Upgrade)
```python
# Option A: Keep existing code (recommended initially)
from graph_analytics_ai import GAEOrchestrator, AnalysisConfig

# Option B: Try AI features (when ready)
from graph_analytics_ai.ai import AIWorkflowOrchestrator
# Add AI_WORKFLOW_ENABLED=true to .env
# Add OPENROUTER_API_KEY to .env
```

### Project 3: psi-graph-analytics (Gradual Adoption)
```python
# Step 1: Keep existing manual workflow
orchestrator = GAEOrchestrator()

# Step 2: Add AI for schema analysis only
from graph_analytics_ai.ai import SchemaAnalyzer
schema = SchemaAnalyzer().analyze_database("my_db")

# Step 3: Add AI for use case generation
from graph_analytics_ai.ai import UseCaseGenerator
use_cases = UseCaseGenerator().generate(...)

# Step 4: Full AI workflow (when confident)
from graph_analytics_ai.ai import AIWorkflowOrchestrator
workflow = AIWorkflowOrchestrator()
```

## API Stability Guarantees

### Guaranteed Stable (No Breaking Changes)

| Component | Status | Guarantee |
|-----------|--------|-----------|
| `GAEOrchestrator` | Existing | ✅ No changes |
| `AnalysisConfig` | Existing | ✅ No changes |
| `AnalysisResult` | Existing | ✅ No changes |
| `GAEManager` | Existing | ✅ No changes |
| `GenAIGAEConnection` | Existing | ✅ No changes |
| `get_arango_config()` | Existing | ✅ No changes |
| `get_gae_config()` | Existing | ✅ No changes |
| All result management | Existing | ✅ No changes |
| All query helpers | Existing | ✅ No changes |
| All export utilities | Existing | ✅ No changes |

### New Optional APIs (AI Features)

| Component | Status | Stability |
|-----------|--------|-----------|
| `AIWorkflowOrchestrator` | New | 🆕 Opt-in |
| `LLMProvider` | New | 🆕 Opt-in |
| `SchemaAnalyzer` | New | 🆕 Opt-in |
| `PRDGenerator` | New | 🆕 Opt-in |
| `UseCaseGenerator` | New | 🆕 Opt-in |
| `ReportGenerator` | New | 🆕 Opt-in |

## Version Compatibility

### v1.2.0 (Current)
- Core graph analytics functionality
- No AI features
- All current functionality stable

### v1.3.0 - v1.9.0 (AI Foundation)
- ✅ All v1.2.0 functionality unchanged
- 🆕 AI features added incrementally
- 🆕 Each version adds new optional features
- ✅ No breaking changes

### v2.0.0 (Complete AI Workflow)
- ✅ All v1.2.0 functionality unchanged
- 🆕 Complete AI workflow available
- 🆕 Full feature parity with roadmap
- ✅ No breaking changes

### v2.1.0+ (Agentic)
- ✅ All previous functionality unchanged
- 🆕 Agentic workflow mode
- 🆕 Optional advanced features
- ✅ No breaking changes

## Error Handling Compatibility

### Existing Error Handling (Preserved)
```python
try:
    result = orchestrator.run_analysis(config)
except ConfigurationError as e:
    # Same error types
    # Same error messages
    # Same error handling
    pass
```

### AI Feature Errors (New, Separate)
```python
from graph_analytics_ai.ai import AIWorkflowError

try:
    result = workflow.run_complete_workflow(...)
except AIWorkflowError as e:
    # New error type for AI features
    # Doesn't affect existing code
    pass
except ConfigurationError as e:
    # Existing errors still work the same
    pass
```

## Performance Compatibility

### Existing Code Performance
```
Import time: <100ms (unchanged)
Analysis execution: Same as v1.2.0
Memory usage: Same as v1.2.0
```

### AI Features Performance
```
Import time (with AI): ~200ms (only if importing ai module)
AI workflow: +LLM latency (customer choice of model)
Core analysis: Same performance (reuses existing code)
```

**Key:** Existing code performance is NOT impacted by AI features.

## Summary: Zero Impact on Existing Code

| Aspect | Impact on Existing Code |
|--------|------------------------|
| **Imports** | ✅ No changes required |
| **API** | ✅ No breaking changes |
| **Configuration** | ✅ Existing config sufficient |
| **Dependencies** | ✅ No new required dependencies |
| **Performance** | ✅ No degradation |
| **Tests** | ✅ All existing tests pass |
| **Behavior** | ✅ Identical to v1.2.0 |
| **Migration** | ✅ No migration needed |

## Customer Decision Tree

```
Do you want to use AI features?
│
├─ NO → ✅ Perfect! Nothing changes.
│        Your code works exactly as before.
│
└─ YES → Two options:
         │
         ├─ Option A: Try AI features (opt-in)
         │   1. Add AI_WORKFLOW_ENABLED=true to .env
         │   2. Add OPENROUTER_API_KEY to .env
         │   3. pip install graph-analytics-ai[ai]
         │   4. Import from graph_analytics_ai.ai
         │   5. Your existing code still works!
         │
         └─ Option B: Gradual adoption
             1. Keep existing workflow
             2. Try schema analyzer only
             3. Try use case generator only
             4. Eventually try full workflow
             5. Mix AI and manual as needed
```

## The Promise

**We guarantee:**

1. ✅ Your existing code will continue to work without any changes
2. ✅ No new required dependencies
3. ✅ No new required configuration
4. ✅ No performance impact on existing workflows
5. ✅ All existing tests will pass
6. ✅ AI features are 100% optional
7. ✅ You control when and how to adopt AI features
8. ✅ You can mix AI and manual workflows
9. ✅ You can disable AI features at any time
10. ✅ No vendor lock-in - you control your LLM provider

**This is backward compatibility done right.**
