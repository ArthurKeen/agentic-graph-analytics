# GAE Algorithm Discovery Investigation

**Date**: December 18, 2025  
**Issue**: Templates generated call out algorithms that are not supported by GAE

---

## Current Situation

### ❌ Problem
The library defines 8 algorithms in `AlgorithmType` enum:
1. PageRank ✅ (supported)
2. Louvain ❌ (NOT supported by GAE)
3. Shortest Path ❌ (NOT in GAE base class)
4. Betweenness Centrality ❌ (NOT fully implemented)
5. Closeness Centrality ❌ (NOT in GAE base class)
6. Label Propagation ✅ (supported)
7. WCC (Weakly Connected Components) ✅ (supported)
8. SCC (Strongly Connected Components) ✅ (supported)

### ✅ Actually Supported by GAE
Based on the `GAEConnectionBase` abstract class, GAE currently supports:

```python
class GAEConnectionBase(ABC):
    def run_pagerank(self, graph_id, damping_factor, maximum_supersteps)
    def run_wcc(self, graph_id)
    def run_scc(self, graph_id)
    def run_label_propagation(self, graph_id, start_label_attribute, ...)
```

**4 algorithms**: PageRank, WCC, SCC, Label Propagation

---

## Investigation Results

### GAE API Endpoints

Based on code analysis, the GAE Engine API provides these endpoints:

**AMP (Managed Platform)**:
- Base URL: `{deployment_url}:{port}/graph-analytics/api/graphanalytics/v1`
- Engine API: `{engine_url}/v1/`

**Self-Managed (GenAI Platform)**:
- Base URL: `{db_endpoint}/gral/{short_id}`
- Engine API: `{base_url}/v1/`

### Available Engine API Endpoints

```
GET  /v1/version              - Get engine API version
POST /v1/loaddata             - Load graph into engine
POST /v1/pagerank             - Run PageRank
POST /v1/wcc                  - Run Weakly Connected Components
POST /v1/scc                  - Run Strongly Connected Components
POST /v1/labelpropagation     - Run Label Propagation
POST /v1/storeresults         - Store results to database
GET  /v1/jobs/{job_id}        - Get job status
GET  /v1/graphs/{graph_id}    - Get graph details
GET  /v1/graphs               - List graphs
DELETE /v1/graphs/{graph_id}  - Delete graph
```

### ⚠️ No Algorithm Discovery Endpoint

**Key Finding**: GAE does not provide an endpoint to query supported algorithms.

The `/v1/version` endpoint returns version information but **not** a list of supported algorithms.

---

## Solutions

### Option 1: Hardcode Supported Algorithms ⭐ Recommended

**Approach**: Maintain an accurate list based on GAE base class

```python
# graph_analytics_ai/ai/templates/models.py

class AlgorithmType(Enum):
    """GAE algorithm types - ONLY SUPPORTED ALGORITHMS."""
    PAGERANK = "pagerank"
    LABEL_PROPAGATION = "label_propagation"
    WCC = "wcc"  # Weakly Connected Components
    SCC = "scc"  # Strongly Connected Components


# Remove unsupported algorithms:
# - LOUVAIN (not in GAE)
# - SHORTEST_PATH (not implemented)
# - BETWEENNESS_CENTRALITY (not fully implemented)
# - CLOSENESS_CENTRALITY (not implemented)
```

**Pros**:
- ✅ Immediate fix
- ✅ No API changes needed
- ✅ Clear and explicit
- ✅ Matches `GAEConnectionBase` implementation

**Cons**:
- ❌ Requires manual updates if GAE adds algorithms

---

### Option 2: Runtime Validation with Try/Catch

**Approach**: Attempt to use algorithm, catch errors

```python
# graph_analytics_ai/gae_orchestrator.py

def _run_algorithm(self, result: AnalysisResult):
    """Run the configured algorithm with validation."""
    result.status = AnalysisStatus.ALGORITHM_RUNNING
    
    params = {
        'graph_id': result.graph_id,
        **result.config.algorithm_params
    }
    
    try:
        if result.config.algorithm == "pagerank":
            job_info = self.gae.run_pagerank(**params)
        elif result.config.algorithm == "label_propagation":
            job_info = self.gae.run_label_propagation(**params)
        elif result.config.algorithm == "wcc":
            job_info = self.gae.run_wcc(**params)
        elif result.config.algorithm == "scc":
            job_info = self.gae.run_scc(**params)
        else:
            raise ValueError(
                f"Unsupported algorithm: {result.config.algorithm}. "
                f"Supported algorithms: pagerank, label_propagation, wcc, scc"
            )
    except AttributeError as e:
        raise ValueError(
            f"Algorithm '{result.config.algorithm}' is not implemented in GAE connection"
        ) from e
```

**Pros**:
- ✅ Runtime validation
- ✅ Clear error messages

**Cons**:
- ❌ Fails at execution time (not generation time)
- ❌ Wastes resources

---

### Option 3: Algorithm Registry with Validation

**Approach**: Create a centralized registry

```python
# graph_analytics_ai/algorithms.py (NEW FILE)

from enum import Enum
from typing import Dict, Set, List
from dataclasses import dataclass


class AlgorithmType(Enum):
    """Supported GAE algorithms."""
    PAGERANK = "pagerank"
    LABEL_PROPAGATION = "label_propagation"
    WCC = "wcc"
    SCC = "scc"


@dataclass
class AlgorithmInfo:
    """Information about a GAE algorithm."""
    name: str
    display_name: str
    description: str
    has_parameters: bool
    default_parameters: Dict


# Registry of supported algorithms
SUPPORTED_ALGORITHMS: Dict[AlgorithmType, AlgorithmInfo] = {
    AlgorithmType.PAGERANK: AlgorithmInfo(
        name="pagerank",
        display_name="PageRank",
        description="Measures node importance based on link structure",
        has_parameters=True,
        default_parameters={
            "damping_factor": 0.85,
            "maximum_supersteps": 100
        }
    ),
    AlgorithmType.WCC: AlgorithmInfo(
        name="wcc",
        display_name="Weakly Connected Components",
        description="Finds connected components (undirected)",
        has_parameters=False,
        default_parameters={}
    ),
    AlgorithmType.SCC: AlgorithmInfo(
        name="scc",
        display_name="Strongly Connected Components",
        description="Finds connected components (directed)",
        has_parameters=False,
        default_parameters={}
    ),
    AlgorithmType.LABEL_PROPAGATION: AlgorithmInfo(
        name="label_propagation",
        display_name="Label Propagation",
        description="Community detection via label propagation",
        has_parameters=True,
        default_parameters={
            "start_label_attribute": "_key",
            "synchronous": False,
            "random_tiebreak": False,
            "maximum_supersteps": 100
        }
    ),
}


def is_algorithm_supported(algorithm: str) -> bool:
    """Check if an algorithm is supported by GAE."""
    try:
        algo_type = AlgorithmType(algorithm)
        return algo_type in SUPPORTED_ALGORITHMS
    except ValueError:
        return False


def get_supported_algorithms() -> List[str]:
    """Get list of supported algorithm names."""
    return [algo.value for algo in SUPPORTED_ALGORITHMS.keys()]


def validate_algorithm(algorithm: str) -> None:
    """Validate that algorithm is supported, raise error if not."""
    if not is_algorithm_supported(algorithm):
        supported = ", ".join(get_supported_algorithms())
        raise ValueError(
            f"Algorithm '{algorithm}' is not supported by GAE. "
            f"Supported algorithms: {supported}"
        )
```

**Usage**:

```python
# In template generator
from graph_analytics_ai.algorithms import validate_algorithm, get_supported_algorithms

def generate_templates(self, use_cases, schema):
    for use_case in use_cases:
        algorithm = self._select_algorithm(use_case)
        
        # Validate before creating template
        validate_algorithm(algorithm)
        
        template = AnalysisTemplate(...)
```

**Pros**:
- ✅ Centralized registry
- ✅ Early validation (at generation time)
- ✅ Easy to add new algorithms
- ✅ Provides algorithm metadata

**Cons**:
- ❌ Still requires manual maintenance
- ❌ Additional complexity

---

### Option 4: Query GAE Version and Infer

**Approach**: Use version info to infer capabilities

```python
def get_supported_algorithms(gae_connection) -> List[str]:
    """
    Get supported algorithms based on GAE version.
    
    Since GAE doesn't provide an algorithm discovery endpoint,
    we maintain a version-to-algorithms mapping.
    """
    version_info = gae_connection.get_engine_version()
    version = version_info.get('version', 'unknown')
    
    # Mapping of GAE version to supported algorithms
    VERSION_ALGORITHMS = {
        'default': ['pagerank', 'wcc', 'scc', 'label_propagation'],
        '1.0': ['pagerank', 'wcc', 'scc'],
        '2.0': ['pagerank', 'wcc', 'scc', 'label_propagation'],
        # Future versions can add more
    }
    
    return VERSION_ALGORITHMS.get(version, VERSION_ALGORITHMS['default'])
```

**Pros**:
- ✅ Version-aware
- ✅ Runtime query

**Cons**:
- ❌ Requires version-to-algorithm mapping maintenance
- ❌ No guarantee GAE version correlates with algorithms

---

## Recommended Solution

### Immediate Fix (Option 1)

1. **Update `AlgorithmType` enum** to only include supported algorithms:

```python
# graph_analytics_ai/ai/templates/models.py

class AlgorithmType(Enum):
    """GAE algorithm types - ONLY VERIFIED SUPPORTED ALGORITHMS."""
    PAGERANK = "pagerank"
    LABEL_PROPAGATION = "label_propagation"
    WCC = "wcc"  # Weakly Connected Components
    SCC = "scc"  # Strongly Connected Components
```

2. **Update `USE_CASE_TO_ALGORITHM` mapping**:

```python
# graph_analytics_ai/ai/templates/generator.py

USE_CASE_TO_ALGORITHM = {
    UseCaseType.CENTRALITY: [
        AlgorithmType.PAGERANK
    ],
    UseCaseType.COMMUNITY: [
        AlgorithmType.WCC,
        AlgorithmType.SCC,
        AlgorithmType.LABEL_PROPAGATION  # Add label prop for community
    ],
    UseCaseType.PATHFINDING: [
        AlgorithmType.PAGERANK  # Best available for influence paths
    ],
    UseCaseType.PATTERN: [
        AlgorithmType.WCC  # For pattern detection
    ],
    UseCaseType.ANOMALY: [
        AlgorithmType.WCC,  # For anomaly clusters
        AlgorithmType.PAGERANK
    ],
    UseCaseType.RECOMMENDATION: [
        AlgorithmType.PAGERANK
    ],
    UseCaseType.SIMILARITY: [
        AlgorithmType.WCC,
        AlgorithmType.LABEL_PROPAGATION
    ]
}
```

3. **Update tests** to only expect supported algorithms

4. **Add validation** in `GAEOrchestrator._run_algorithm()`

---

### Future Enhancement (Option 3)

When GAE adds new algorithms:
1. Create `algorithms.py` with registry
2. Add algorithm to registry
3. Add method to base class
4. Update enum
5. Run tests

---

## Files to Update

### 1. `graph_analytics_ai/ai/templates/models.py`
- Remove unsupported algorithms from `AlgorithmType`
- Update `DEFAULT_ALGORITHM_PARAMS` to only include supported
- Update test count expectations

### 2. `graph_analytics_ai/ai/templates/generator.py`
- Update `USE_CASE_TO_ALGORITHM` mapping
- Add validation for algorithm support

### 3. `tests/unit/ai/templates/test_generator.py`
- Fix failing tests to expect only supported algorithms

### 4. `tests/unit/ai/templates/test_models.py`
- Update algorithm count test (expect 4, not 8)
- Remove tests for unsupported algorithms

### 5. `graph_analytics_ai/gae_orchestrator.py`
- Add better error message for unsupported algorithms

---

## Implementation Steps

1. ✅ Identify supported algorithms (DONE - 4 algorithms)
2. ⏳ Remove unsupported from enum
3. ⏳ Update use case mappings
4. ⏳ Fix failing tests
5. ⏳ Add validation
6. ⏳ Test with real workflow

---

## Summary

**Problem**: Library defines 8 algorithms, but GAE only supports 4  
**Root Cause**: No algorithm discovery API in GAE  
**Solution**: Hardcode supported algorithms based on `GAEConnectionBase`  
**Supported**: PageRank, WCC, SCC, Label Propagation  
**Action**: Update enum, mappings, and tests

**Next Steps**: Would you like me to implement the recommended solution?

