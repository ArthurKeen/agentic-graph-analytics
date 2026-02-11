# Analysis Catalog - ArangoDB Named Graph

## Graph Name
`analysis_catalog_graph`

## Overview

The Analysis Catalog uses an **ArangoDB named graph** to model relationships between analysis entities. This enables powerful graph traversals and visualizations using ArangoDB's built-in graph capabilities.

## Graph Structure

### Vertex Collections (Document Collections)

1. **`analysis_epochs`** - Time-series groupings
2. **`analysis_requirements`** - Extracted requirements (agentic workflow)
3. **`analysis_use_cases`** - Generated use cases (agentic workflow)
4. **`analysis_templates`** - Analysis templates (agentic workflow)
5. **`analysis_executions`** - Individual analysis runs

### Edge Collections

1. **`analysis_lineage_edges`** - Lineage relationships
   - Requirements → Use Cases
   - Use Cases → Templates
   - Templates → Executions

2. **`analysis_epoch_edges`** - Epoch containment relationships
   - Epochs → Requirements
   - Epochs → Use Cases
   - Epochs → Templates
   - Epochs → Executions

## Visual Representation

```
analysis_catalog_graph
│
├── Lineage Chain (analysis_lineage_edges):
│   │
│   analysis_requirements
│          ↓ (generates)
│   analysis_use_cases
│          ↓ (generates)
│   analysis_templates
│          ↓ (executes)
│   analysis_executions
│
└── Epoch Containment (analysis_epoch_edges):
    │
    analysis_epochs
           ↓ (contains)
           ├──> analysis_requirements
           ├──> analysis_use_cases
           ├──> analysis_templates
           └──> analysis_executions
```

## Graph Queries

### 1. Traverse Complete Lineage

```aql
// Find all descendants of a requirement
FOR v, e, p IN 1..10 OUTBOUND
  'analysis_requirements/req-123'
  GRAPH 'analysis_catalog_graph'
  PRUNE e._from LIKE 'analysis_executions/%'
  FILTER e._from LIKE 'analysis_lineage_edges/%'
  RETURN {
    level: LENGTH(p.vertices),
    type: PARSE_IDENTIFIER(v).collection,
    document: v
  }
```

### 2. Find All Entities in an Epoch

```aql
// Get all analysis entities for an epoch
FOR v IN 1..1 OUTBOUND
  'analysis_epochs/epoch-2026-01-07'
  GRAPH 'analysis_catalog_graph'
  FILTER PARSE_IDENTIFIER(v._id).collection IN [
    'analysis_requirements',
    'analysis_use_cases',
    'analysis_templates',
    'analysis_executions'
  ]
  RETURN {
    type: PARSE_IDENTIFIER(v).collection,
    id: v._key,
    summary: v.name OR v.title OR v.algorithm
  }
```

### 3. Impact Analysis

```aql
// What would be affected if we change this requirement?
FOR v IN 1..10 OUTBOUND
  'analysis_requirements/req-123'
  GRAPH 'analysis_catalog_graph'
  OPTIONS {bfs: true, uniqueVertices: 'global'}
  COLLECT type = PARSE_IDENTIFIER(v).collection INTO items = v
  RETURN {
    affected_type: type,
    affected_count: LENGTH(items),
    affected_ids: items[*]._key
  }
```

### 4. Lineage Path

```aql
// Show complete path from requirement to execution
FOR v, e, p IN 1..10 OUTBOUND
  'analysis_requirements/req-123'
  GRAPH 'analysis_catalog_graph'
  FILTER v._id == 'analysis_executions/exec-456'
  LIMIT 1
  RETURN {
    path_length: LENGTH(p.vertices),
    path: [
      FOR vertex IN p.vertices
      RETURN {
        type: PARSE_IDENTIFIER(vertex).collection,
        id: vertex._key,
        name: vertex.name OR vertex.title OR vertex.algorithm
      }
    ]
  }
```

### 5. Time-Series Comparison

```aql
// Compare PageRank results across epochs
FOR epoch IN analysis_epochs
  FILTER epoch.tags ANY IN ['production']
  SORT epoch.timestamp ASC
  
  LET executions = (
    FOR v IN 1..1 OUTBOUND epoch
      GRAPH 'analysis_catalog_graph'
      FILTER PARSE_IDENTIFIER(v._id).collection == 'analysis_executions'
      FILTER v.algorithm == 'pagerank'
      RETURN v
  )
  
  RETURN {
    epoch_name: epoch.name,
    epoch_date: epoch.timestamp,
    pagerank_count: LENGTH(executions),
    avg_execution_time: AVG(executions[*].performance_metrics.execution_time_seconds),
    total_results: SUM(executions[*].result_count)
  }
```

## Graph Features

### Automatic Creation

The graph is automatically created when `ArangoDBStorage` is initialized:

```python
from graph_analytics_ai.catalog import AnalysisCatalog
from graph_analytics_ai.catalog.storage import ArangoDBStorage
from graph_analytics_ai.db_connection import get_db_connection

# Initialize storage (auto-creates graph)
db = get_db_connection()
storage = ArangoDBStorage(db)  # Creates analysis_catalog_graph
```

### Graph Properties

- **Name**: `analysis_catalog_graph`
- **Type**: Named graph (not SmartGraph)
- **Edge Definitions**: 2 edge collections
- **Vertex Collections**: 5 document collections
- **Directionality**: Directed edges
- **Cycles**: Not allowed (DAG structure for lineage)

### Benefits of Using Named Graph

1. **Unified Queries**: Single graph name for all traversals
2. **Web UI Visualization**: View in ArangoDB web interface
3. **Graph Algorithms**: Use built-in graph algorithms (shortest path, centrality)
4. **Performance**: Optimized graph traversals
5. **Consistency**: Edge constraints ensure valid relationships

## Viewing in ArangoDB Web UI

1. Open ArangoDB web interface
2. Navigate to **GRAPHS** section
3. Select `analysis_catalog_graph`
4. Click any vertex to explore relationships
5. Use graph visualization tools

## Migration from Foreign Keys

The current implementation maintains **both** approaches:

1. **Foreign Key Fields**: `requirements_id`, `use_case_id`, `template_id`, `epoch_id` (for backwards compatibility and direct queries)
2. **Graph Edges**: Edge documents in `analysis_lineage_edges` and `analysis_epoch_edges` (for graph traversals)

This dual approach provides:
- **Fast direct queries** using foreign key indexes
- **Powerful traversals** using graph capabilities
- **Flexibility** to use either approach based on use case

## Performance Considerations

- **Document Queries**: Use foreign keys for simple lookups (faster)
- **Traversals**: Use graph for multi-hop relationships (more powerful)
- **Hybrid**: Combine both for optimal performance

Example:
```python
# Fast: Direct foreign key lookup
execution = storage.get_execution("exec-123")
template_id = execution.template_id
template = storage.get_template(template_id)

# Powerful: Graph traversal for complete lineage
lineage = tracker.get_complete_lineage("exec-123")  # Uses graph traversal
```

## Future Enhancements

1. **SmartGraph**: For multi-region deployments
2. **Graph Algorithms**: Apply centrality measures to identify key requirements
3. **Satellite Collections**: For large result samples
4. **Graph Pregel**: For distributed graph computations

---

**Status**: Implemented in v3.2.0  
**Collections**: 5 vertex + 2 edge = 7 total  
**Graph Name**: `analysis_catalog_graph`  
**Auto-Created**: Yes (on first initialization)

