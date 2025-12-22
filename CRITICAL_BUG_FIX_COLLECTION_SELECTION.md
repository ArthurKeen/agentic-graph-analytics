# CRITICAL BUG FIX: Collection Selection and Algorithm Execution

**Bug ID**: Collection-Expansion-001  
**Date**: December 22, 2025  
**Priority**: CRITICAL  
**Status**: FIX IN PROGRESS

---

## Problem Summary

Collection selection is not being respected during execution:
- **Template**: 6 collections, algorithm=wcc
- **Actual execution**: 17 collections, algorithm=pagerank
- **Impact**: 50x cost overrun, validation failures, production blocked

---

## Root Cause Analysis

After investigation, I found **TWO critical bugs**:

### Bug #1: AnalysisConfig has a default algorithm of "pagerank"

**Location**: `graph_analytics_ai/gae_orchestrator.py` line 66

```python
@dataclass
class AnalysisConfig:
    algorithm: str = "pagerank"  # ❌ DANGEROUS DEFAULT!
```

**Problem**: If the algorithm is not explicitly passed or is None, it defaults to "pagerank". This explains why WCC templates run PageRank!

### Bug #2: Server-side collection expansion (suspected)

The GAE API might be expanding collections based on edge definitions, despite explicit collection lists being provided. Need to verify with actual execution logs.

---

## Fix Strategy

### Fix #1: Remove dangerous default
Make algorithm a required field with no default:

```python
@dataclass
class AnalysisConfig:
    # Analysis identification
    name: str
    description: str = ""
    
    # Graph configuration
    vertex_collections: List[str] = field(default_factory=list)
    edge_collections: List[str] = field(default_factory=list)
    
    # Algorithm configuration (NO DEFAULT!)
    algorithm: str  # ❌ REMOVE = "pagerank"
```

### Fix #2: Add comprehensive debug logging

Add logging at every step to track:
1. What template specifies
2. What executor receives
3. What AnalysisConfig is created with
4. What GAE receives
5. What actually executes

### Fix #3: Add validation

Ensure algorithm and collections are never None or empty when they shouldn't be.

---

## Implementation Plan

1. ✅ Add debug logging to executor
2. ✅ Add debug logging to orchestrator  
3. ✅ Remove dangerous default from AnalysisConfig
4. ✅ Add validation in executor
5. ✅ Add integration test
6. ⏸️ Wait for customer to test

---

## Files to Modify

1. `graph_analytics_ai/gae_orchestrator.py`
   - Remove `= "pagerank"` default from algorithm field
   
2. `graph_analytics_ai/ai/execution/executor.py`
   - Add debug logging in `_template_to_config()`
   - Add validation that algorithm is not None/empty
   
3. `graph_analytics_ai/gae_orchestrator.py`
   - Add debug logging in `_load_graph()`
   - Add debug logging in `_run_algorithm()`

4. `tests/test_collection_selection_bug.py` (NEW)
   - Integration test to prevent regression

---

## Debug Logging to Add

See BUG_REPORT_FOR_LIBRARY_TEAM.md for exact code to add.

---

## Status

- Investigation: ✅ COMPLETE
- Fix implementation: 🔄 IN PROGRESS
- Testing: ⏸️ PENDING
- Deployment: ⏸️ PENDING

---

**Next Step**: Implement the fix and add comprehensive logging.

