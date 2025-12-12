# Gap Analysis and Implementation Plan

**Date:** 2025-01-27  
**Project:** psi-graph-analytics migration to graph-analytics-ai  
**Status:** Planning - Ready for Implementation

---

## Executive Summary

This document outlines the gaps identified between the psi-graph-analytics project and the graph-analytics-ai library, and provides a detailed plan to address them. The gaps are prioritized by criticality and impact on migration.

**Key Principle:** Make the library meet our needs, not work around gaps.

---

## Gap Analysis Summary

### Critical Gaps (Must Fix Before Migration)

1. **Named Graph Support** - `load_graph()` doesn't support `graph_name` parameter
2. **Service Discovery** - `list_services()` method missing

### High Priority Gaps (Should Fix)

3. **Graph Management** - `list_graphs()` and `delete_graph()` methods missing
4. **Job Management** - `wait_for_job()` and `list_jobs()` methods missing

### Medium Priority Gaps (Nice to Have)

5. **Database Parameter** - `store_results()` requires explicit `database` parameter (psi uses `self.db_name`)
6. **Connection Testing** - `test_connection()` method missing

### Low Priority (Easy Fixes)

7. **Method Name** - `get_job_status()` vs `get_job()` (just rename calls)

---

## Detailed Gap Analysis

### Gap 1: Named Graph Support  **CRITICAL**

**Current psi Implementation:**
```python
gae.load_graph(graph_name='investigator_network')
# OR
gae.load_graph(
    vertex_collections=['persons'],
    edge_collections=['edges']
)
```

**Library Implementation:**
```python
gae.load_graph(
    database='restore',
    vertex_collections=['persons'],
    edge_collections=['edges']
)
# graph_name parameter NOT supported
```

**Impact:** HIGH - Many scripts use named graphs  
**Files Affected:** Multiple example scripts in psi-graph-analytics

**Required Enhancement:**
- Add `graph_name` parameter to `load_graph()` in both `GAEManager` and `GenAIGAEConnection`
- Support both named graphs and collection-based loading
- If `graph_name` provided, use it; otherwise require collections
- Update base class signature

---

### Gap 2: Service Discovery  **CRITICAL**

**Current psi Implementation:**
```python
services = gae.list_services()
gae_services = [s for s in services if s.get('serviceId', '').startswith('arangodb-gral')]
if gae_services:
    gae.engine_id = gae_services[0]['serviceId']
```

**Library Implementation:** Method doesn't exist

**Impact:** HIGH - Used in multiple scripts for service discovery  
**Files Affected:** Multiple scripts that check for existing services

**Required Enhancement:**
- Add `list_services()` method to `GenAIGAEConnection`
- Call `/gen-ai/v1/list_services` endpoint
- Return list of service dictionaries
- Used for discovering existing GAE services

---

### Gap 3: Graph Management  **HIGH PRIORITY**

**Current psi Implementation:**
```python
graphs = gae.list_graphs()
graph_9 = [g for g in graphs if g.get('graph_id') == 9]
if not graph_9:
    load_result = gae.load_graph(graph_name='investigator_network')

gae.delete_graph(graph_id='9')
```

**Library Implementation:** Methods don't exist

**Impact:** MEDIUM - Used for checking if graph is already loaded, cleanup  
**Files Affected:** Scripts that manage multiple graphs

**Required Enhancement:**
- Add `list_graphs()` method to `GenAIGAEConnection`
  - Call `/gral/{short_id}/v1/graphs` endpoint
  - Return list of graph dictionaries
- Add `delete_graph(graph_id)` method to `GenAIGAEConnection`
  - Call `DELETE /gral/{short_id}/v1/graphs/{graph_id}` endpoint
  - Return deletion result

---

### Gap 4: Job Management  **HIGH PRIORITY**

**Current psi Implementation:**
```python
gae.wait_for_job(job_id, poll_interval=2, max_wait=3600)
jobs = gae.list_jobs()
```

**Library Implementation:** Methods don't exist (but `get_job()` exists)

**Impact:** MEDIUM - Used for job monitoring and waiting  
**Files Affected:** Scripts that wait for job completion

**Required Enhancement:**
- Add `wait_for_job()` method to `GenAIGAEConnection`
  - Poll `get_job()` until status is 'completed' or 'failed'
  - Support `poll_interval` and `max_wait` parameters
  - Return final job status
- Add `list_jobs()` method to `GenAIGAEConnection`
  - Call `/gral/{short_id}/v1/jobs` endpoint
  - Return list of job dictionaries

---

### Gap 5: Database Parameter  **MEDIUM PRIORITY**

**Current psi Implementation:**
```python
gae.store_results(
    job_ids=[job_id],
    target_collection='persons',
    attribute_names=['pagerank_score']
)
# Uses self.db_name internally
```

**Library Implementation:**
```python
gae.store_results(
    database='restore',  # Required parameter
    target_collection='persons',
    job_ids=[job_id],
    attribute_names=['pagerank_score']
)
```

**Impact:** MEDIUM - All `store_results()` calls need updating  
**Files Affected:** All scripts that store results

**Required Enhancement:**
- Make `database` parameter optional in `store_results()`
- If not provided, use `self.db_name` (for GenAIGAEConnection)
- Maintain backward compatibility for explicit database parameter

---

### Gap 6: Connection Testing  **LOW PRIORITY**

**Current psi Implementation:**
```python
if gae.test_connection():
    print("Connection OK")
```

**Library Implementation:** Method doesn't exist

**Impact:** LOW - Nice to have, not critical  
**Files Affected:** Test scripts

**Required Enhancement:**
- Add `test_connection()` method to `GenAIGAEConnection`
  - Try to get JWT token
  - Try to list services or get engine version
  - Return True/False

---

### Gap 7: Method Name Difference  **LOW PRIORITY**

**Current psi:** `get_job_status(job_id)`  
**Library:** `get_job(job_id)`

**Impact:** LOW - Easy to rename in migration  
**Action:** Update all calls from `get_job_status` to `get_job`

---

## Implementation Plan

### Phase 1: Critical Gaps (Do First) ⭐

**Estimated Time:** 2-3 days

#### Task 1.1: Add Named Graph Support

**Files to Modify:**
- `graph_analytics_ai/gae_connection.py`

**Changes:**
1. Update `GAEConnectionBase.load_graph()` signature:
   ```python
   def load_graph(
       self,
       database: str,
       vertex_collections: Optional[List[str]] = None,
       edge_collections: Optional[List[str]] = None,
       graph_name: Optional[str] = None,  # NEW
       vertex_attributes: Optional[List[str]] = None
   ) -> Dict[str, Any]:
   ```

2. Update `GenAIGAEConnection.load_graph()`:
   - Support `graph_name` parameter
   - If `graph_name` provided, use it in payload
   - If collections provided, use them
   - Validate that either `graph_name` OR collections are provided
   - Use `self.db_name` if `database` not provided (for backward compatibility)

3. Update `GAEManager.load_graph()`:
   - Add `graph_name` parameter support
   - Check if AMP API supports named graphs (may need to verify)

**Testing:**
- Test named graph loading
- Test collection-based loading
- Test error when neither provided
- Test backward compatibility

---

#### Task 1.2: Add Service Discovery

**Files to Modify:**
- `graph_analytics_ai/gae_connection.py`

**Changes:**
1. Add `list_services()` method to `GenAIGAEConnection`:
   ```python
   def list_services(self) -> List[Dict[str, Any]]:
       """List all running GenAI services."""
       url = f"{self.db_endpoint}/gen-ai/v1/list_services"
       headers = self._get_headers()
       response = requests.post(url, headers=headers, ...)
       return response.json().get('services', [])
   ```

**Testing:**
- Test listing services
- Test with no services running
- Test error handling

---

### Phase 2: High Priority Gaps

**Estimated Time:** 2-3 days

#### Task 2.1: Add Graph Management

**Files to Modify:**
- `graph_analytics_ai/gae_connection.py`

**Changes:**
1. Add `list_graphs()` method:
   ```python
   def list_graphs(self) -> List[Dict[str, Any]]:
       """List all graphs loaded in the GAE."""
       engine_url = self._get_engine_url()
       url = f"{engine_url}/v1/graphs"
       headers = self._get_headers()
       response = requests.get(url, headers=headers, ...)
       return response.json()
   ```

2. Add `delete_graph()` method:
   ```python
   def delete_graph(self, graph_id: str) -> Dict[str, Any]:
       """Delete a loaded graph from GAE engine memory."""
       engine_url = self._get_engine_url()
       url = f"{engine_url}/v1/graphs/{graph_id}"
       headers = self._get_headers()
       response = requests.delete(url, headers=headers, ...)
       return response.json()
   ```

**Testing:**
- Test listing graphs
- Test deleting graphs
- Test error handling

---

#### Task 2.2: Add Job Management

**Files to Modify:**
- `graph_analytics_ai/gae_connection.py`

**Changes:**
1. Add `wait_for_job()` method:
   ```python
   def wait_for_job(
       self,
       job_id: str,
       poll_interval: int = 2,
       max_wait: int = 3600
   ) -> Dict[str, Any]:
       """Wait for a job to complete."""
       start_time = time.time()
       while True:
           job = self.get_job(job_id)
           status = job.get('status', {}).get('state', 'unknown')
           
           if status in ('completed', 'failed', 'error'):
               return job
           
           if time.time() - start_time > max_wait:
               raise TimeoutError(f"Job {job_id} did not complete within {max_wait}s")
           
           time.sleep(poll_interval)
   ```

2. Add `list_jobs()` method:
   ```python
   def list_jobs(self) -> List[Dict[str, Any]]:
       """List all jobs on the GAE."""
       engine_url = self._get_engine_url()
       url = f"{engine_url}/v1/jobs"
       headers = self._get_headers()
       response = requests.get(url, headers=headers, ...)
       return response.json()
   ```

**Testing:**
- Test waiting for job completion
- Test timeout handling
- Test listing jobs
- Test error handling

---

### Phase 3: Medium Priority Gaps

**Estimated Time:** 1 day

#### Task 3.1: Make Database Parameter Optional

**Files to Modify:**
- `graph_analytics_ai/gae_connection.py`

**Changes:**
1. Update `GenAIGAEConnection.store_results()`:
   ```python
   def store_results(
       self,
       target_collection: str,
       job_ids: List[str],
       attribute_names: List[str],
       database: Optional[str] = None,  # Make optional
       parallelism: int = 8,
       batch_size: int = 10000
   ) -> Dict[str, Any]:
       database = database or self.db_name  # Use self.db_name if not provided
       # ... rest of implementation
   ```

2. Update base class signature to match

**Testing:**
- Test with explicit database parameter
- Test without database parameter (uses self.db_name)
- Test backward compatibility

---

#### Task 3.2: Add Connection Testing

**Files to Modify:**
- `graph_analytics_ai/gae_connection.py`

**Changes:**
1. Add `test_connection()` method:
   ```python
   def test_connection(self) -> bool:
       """Test connection to GenAI GAE."""
       try:
           self._get_jwt_token()
           # Try to list services or get engine version
           services = self.list_services()
           return True
       except Exception as e:
           print(f"Connection test failed: {e}")
           return False
   ```

**Testing:**
- Test with valid credentials
- Test with invalid credentials
- Test with network issues

---

## Testing Strategy

### Unit Tests
- Add tests for each new method
- Test error handling
- Test edge cases

### Integration Tests
- Test with real self-managed deployment
- Test all new methods end-to-end
- Verify backward compatibility

### Migration Testing
- Test one psi script with enhanced library
- Compare results with original implementation
- Verify all functionality preserved

---

## Migration Impact on Other Projects

### dnb_er / dnb_gae

**Question:** Do these projects need updates?

**Analysis:**
- dnb_er uses AMP deployment (GAEManager)
- dnb_gae (if exists) likely also uses AMP
- Changes to `GenAIGAEConnection` won't affect AMP projects
- Changes to base class may affect both

**Required Updates:**
1. **If `load_graph()` base class signature changes:**
   - dnb_er may need updates if it uses `load_graph()` directly
   - Check if dnb_er uses `GAEOrchestrator` (which calls `load_graph()`)
   - If using orchestrator, may need to update `AnalysisConfig` to support `graph_name`

2. **If `store_results()` signature changes:**
   - dnb_er may need updates if it calls `store_results()` directly
   - Check if dnb_er uses `GAEOrchestrator` (which handles this)

**Recommendation:**
- Review dnb_er codebase to see if it uses these methods directly
- If using `GAEOrchestrator`, may need to enhance `AnalysisConfig` to support named graphs
- Test dnb_er after library enhancements to ensure no regressions

---

## Implementation Checklist

### Phase 1: Critical Gaps
- [ ] Add `graph_name` parameter to `load_graph()`
- [ ] Update base class signature
- [ ] Update `GenAIGAEConnection.load_graph()`
- [ ] Update `GAEManager.load_graph()` (if AMP supports named graphs)
- [ ] Add `list_services()` method
- [ ] Write unit tests
- [ ] Test with real deployment

### Phase 2: High Priority
- [ ] Add `list_graphs()` method
- [ ] Add `delete_graph()` method
- [ ] Add `wait_for_job()` method
- [ ] Add `list_jobs()` method
- [ ] Write unit tests
- [ ] Test with real deployment

### Phase 3: Medium Priority
- [ ] Make `database` parameter optional in `store_results()`
- [ ] Add `test_connection()` method
- [ ] Write unit tests
- [ ] Test with real deployment

### Phase 4: Migration
- [ ] Test library with one psi script
- [ ] Migrate all psi scripts
- [ ] Test dnb_er for regressions
- [ ] Update documentation
- [ ] Remove old psi implementation files

---

## Success Criteria

1.  All critical gaps addressed
2.  All high priority gaps addressed
3.  Library works with psi-graph-analytics scripts
4.  No regressions in dnb_er / dnb_gae
5.  All tests pass
6.  Documentation updated

---

## Next Steps

1. **Review this plan** with team
2. **Start Phase 1** (Critical gaps)
3. **Test with real deployment** after each phase
4. **Begin migration** once all gaps addressed
5. **Verify other projects** (dnb_er) still work

---

**Last Updated:** 2025-01-27  
**Status:** Ready for Implementation

