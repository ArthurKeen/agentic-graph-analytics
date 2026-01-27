# Collection Selection for Graph Algorithms

## Overview

Different graph algorithms have different requirements for which vertex and edge collections they should operate on. This guide explains the **Collection Selection Agent** that automatically determines the appropriate collections for each algorithm.

## The Problem

**Example scenario:**
- Your graph has:
 - **Core collections**: `users`, `products`, `orders`
 - **Satellite collections**: `metadata`, `configs`, `lookup_tables`
 - **Edges**: `purchases`, `views`, `friendships`, `config_refs`

**The issue:**
- **WCC/SCC**: Should exclude satellites (only core graph structure matters)
- **PageRank**: Should include everything (satellites can influence importance)
- **Betweenness**: Should include everything (need full graph for accurate centrality)
- **Label Propagation**: Focus on core (communities in main graph)

Previously, the library would blindly use the first 5 collections for ALL algorithms, which led to:
- Incorrect WCC results (satellites create false components)
- Inefficient execution (processing unnecessary collections)
- Confusing results (why is `metadata` showing up in communities?)

## Solution: CollectionSelector

The `CollectionSelector` class implements algorithm-aware collection selection:

```python
from graph_analytics_ai.ai.templates import CollectionSelector, select_collections_for_algorithm
from graph_analytics_ai.ai.templates.models import AlgorithmType

# Option 1: Use convenience function
selection = select_collections_for_algorithm(
 algorithm=AlgorithmType.WCC,
 schema=my_schema,
 satellite_collections=["metadata", "configs", "lookup_tables"],
 core_collections=["users", "products", "orders"]
)

print(f"Selected vertices: {selection.vertex_collections}")
# Output: ['users', 'products', 'orders']

print(f"Excluded: {selection.excluded_vertices}")
# Output: ['metadata (satellite)', 'configs (satellite)', 'lookup_tables (satellite)']

print(f"Reasoning: {selection.reasoning}")
# Output: "wcc analysis focuses on core graph connectivity. Excluded 3 satellite/metadata
# collections and 1 peripheral edges. This ensures the algorithm finds meaningful
# components in the primary graph structure."

# Option 2: Use the class directly
selector = CollectionSelector()
selection = selector.select_collections(
 algorithm=AlgorithmType.PAGERANK,
 schema=my_schema,
 collection_hints={
 "satellite_collections": ["metadata", "configs"],
 "core_collections": ["users", "products"]
 }
)

print(f"Selected vertices: {selection.vertex_collections}")
# Output: ['users', 'products', 'metadata', 'configs'] # Includes satellites!
```

## Algorithm-Specific Selection Rules

### 1. WCC (Weakly Connected Components)

**Goal**: Find connected components in the core graph structure

**Selection strategy**:
- Include: Core collections, bridge collections
- Exclude: Satellite collections, metadata collections
- Edges: Only those connecting included vertices

**Reasoning**: WCC finds groups of connected entities. Satellite collections (like lookup tables or metadata) would create false components or noise.

**Example**:
```python
# Input: users, products, orders, metadata, configs
# WCC selects: users, products, orders
# Reasoning: Find communities of users/products/orders, ignore reference data
```

### 2. SCC (Strongly Connected Components)

**Goal**: Find strongly connected components (mutual connectivity)

**Selection strategy**:
- Include: Core collections, bridge collections
- Exclude: Satellite collections, metadata collections
- Edges: Directed edges connecting included vertices
- Requires: Directed edges

**Reasoning**: Similar to WCC but stricter - needs directed edges for mutual connectivity.

### 3. PageRank

**Goal**: Calculate importance/influence across the entire network

**Selection strategy**:
- Include: ALL collections (core + satellites)
- Edges: ALL edges
- Focus: Full graph

**Reasoning**: PageRank measures influence through the entire network. Satellites can contribute to importance (e.g., a user connected to important metadata is more important).

**Example**:
```python
# Input: users, products, orders, categories, metadata
# PageRank selects: ALL of them
# Reasoning: Full graph needed for accurate importance calculation
```

### 4. Betweenness Centrality

**Goal**: Find entities that act as bridges between other entities

**Selection strategy**:
- Include: ALL collections
- Edges: ALL edges
- Focus: Full graph

**Reasoning**: To accurately calculate betweenness (how many shortest paths go through a node), you need the complete graph structure.

### 5. Label Propagation

**Goal**: Detect communities based on label spreading

**Selection strategy**:
- Include: Core collections, bridge collections
- Exclude: Satellite collections
- Edges: Edges with sufficient connectivity (min_edge_count: 2)

**Reasoning**: Communities form in the main graph structure. Satellites don't participate in community formation.

## Integration with TemplateGenerator

The `TemplateGenerator` automatically uses `CollectionSelector`:

```python
from graph_analytics_ai.ai.templates import TemplateGenerator

# Initialize with collection hints
generator = TemplateGenerator(
 graph_name="my_graph",
 satellite_collections=["metadata", "configs", "lookup_tables"],
 core_collections=["users", "products", "orders", "categories"]
)

# Generate templates - collection selection happens automatically
templates = generator.generate_templates(use_cases, schema, schema_analysis)

# Check what was selected
for template in templates:
 print(f"\n{template.name}")
 print(f" Algorithm: {template.algorithm.algorithm.value}")
 print(f" Vertices: {template.config.vertex_collections}")
 print(f" Reasoning: {template.metadata.get('collection_selection_reasoning', 'N/A')}")
 
 excluded = template.metadata.get('excluded_collections', {})
 if excluded.get('vertices'):
 print(f" Excluded vertices: {excluded['vertices']}")
```

## Automatic Classification

If you don't provide collection hints, `CollectionSelector` will auto-classify based on heuristics:

```python
# No hints provided
generator = TemplateGenerator(graph_name="my_graph")
# Auto-classification uses:
# - Collection names (looks for 'config', 'metadata', 'lookup', 'setting', 'reference')
# - Document counts (< 100 docs = likely metadata)
# - Edge counts (many edges = likely core)

templates = generator.generate_templates(use_cases, schema)
# Collections will be automatically classified and selected per algorithm
```

**Auto-classification heuristics**:
1. **Satellite keywords**: Collections with names containing:
 - `config`, `setting`, `metadata`, `lookup`, `reference`
2. **Metadata collections**: Collections with < 100 documents
3. **Core collections**: Collections with:
 - Many edges (> 1000) OR
 - Large document count (> 500) AND significant edges (> 100)
4. **Default**: Collections with ≥ 100 documents are considered core

## CollectionRole Enum

Collections are classified into roles:

```python
from graph_analytics_ai.ai.templates import CollectionRole

class CollectionRole(Enum):
 CORE = "core" # Central to graph structure (users, products)
 SATELLITE = "satellite" # Peripheral reference data (configs, lookups)
 BRIDGE = "bridge" # Connects core to other parts (categories)
 METADATA = "metadata" # Supplementary info (tags, attributes)
```

## Manual Override

You can always override automatic selection:

```python
# Get automatic selection
selection = selector.select_collections(
 algorithm=AlgorithmType.WCC,
 schema=my_schema
)

# Override if needed
selection.vertex_collections.append("special_collection")
selection.excluded_vertices.remove("important_satellite")

# Use modified selection in your template
config = TemplateConfig(
 graph_name="my_graph",
 vertex_collections=selection.vertex_collections,
 edge_collections=selection.edge_collections,
 ...
)
```

## Example: Media Analytics Use Case

```python
# Example media graph has:
# - Core: audiences, campaigns, creatives, devices, publishers
# - Satellite: audience_metadata, device_specs, geo_lookups

generator = TemplateGenerator(
 graph_name="example_media_graph",
 satellite_collections=[
 "audience_metadata",
 "device_specs", 
 "geo_lookups",
 "rate_cards"
 ],
 core_collections=[
 "audiences",
 "campaigns",
 "creatives",
 "devices",
 "publishers"
 ]
)

# WCC analysis: Find connected campaign/audience/device clusters
# - Will EXCLUDE metadata, specs, lookups
# - Only uses core collections

# PageRank analysis: Rank campaign/creative importance
# - Will INCLUDE everything
# - Metadata contributes to importance scores
```

## Testing Your Collection Selection

You can test the selection before running algorithms:

```python
from graph_analytics_ai.ai.templates import select_collections_for_algorithm, AlgorithmType

# Test WCC selection
wcc_selection = select_collections_for_algorithm(
 algorithm=AlgorithmType.WCC,
 schema=my_schema,
 satellite_collections=["metadata"]
)

print(f"WCC will use: {wcc_selection.vertex_collections}")
print(f"WCC will exclude: {wcc_selection.excluded_vertices}")
print(f"Estimated size: {wcc_selection.estimated_graph_size}")

# Test PageRank selection
pr_selection = select_collections_for_algorithm(
 algorithm=AlgorithmType.PAGERANK,
 schema=my_schema,
 satellite_collections=["metadata"]
)

print(f"\nPageRank will use: {pr_selection.vertex_collections}")
print(f"PageRank will exclude: {pr_selection.excluded_vertices}")
```

## Best Practices

### 1. Always Specify Satellite Collections

```python
# Good: Explicit satellite specification
generator = TemplateGenerator(
 graph_name="my_graph",
 satellite_collections=["metadata", "configs"]
)

# Works but less accurate: Relies on auto-detection
generator = TemplateGenerator(graph_name="my_graph")
```

### 2. Review Selection Reasoning

```python
templates = generator.generate_templates(use_cases, schema)

for template in templates:
 # Check the reasoning
 reasoning = template.metadata.get('collection_selection_reasoning')
 if reasoning:
 print(f"{template.name}: {reasoning}")
 
 # Verify exclusions make sense
 excluded = template.metadata.get('excluded_collections', {})
 if excluded:
 print(f" Excluded: {excluded}")
```

### 3. Document Your Collection Roles

```python
# In your customer project (e.g., your-customer-project):

# docs/collection_roles.md
"""
# Collection Role Examples

## Core Collections
- audiences: Primary audience entities
- campaigns: Marketing campaigns
- devices: Connected TV devices
- publishers: Content publishers

## Satellite Collections 
- audience_metadata: Reference data for audiences
- device_specs: Technical specifications
- geo_lookups: Geographic reference data

## Bridge Collections
- categories: Connect content to multiple entities
"""
```

### 4. Test with Different Algorithms

```python
# Generate templates for all use cases
templates = generator.generate_templates(use_cases, schema)

# Group by algorithm to verify selection
from collections import defaultdict

by_algorithm = defaultdict(list)
for template in templates:
 algo = template.algorithm.algorithm
 by_algorithm[algo].append(template)

for algo, tmpl_list in by_algorithm.items():
 print(f"\n{algo.value}:")
 print(f" Vertex collections: {tmpl_list[0].config.vertex_collections}")
 print(f" Reasoning: {tmpl_list[0].metadata.get('collection_selection_reasoning')}")
```

## Troubleshooting

### Issue: WCC finding too many components

**Problem**: WCC is finding dozens of tiny components

**Solution**: Likely including satellite collections. Verify:

```python
selection = select_collections_for_algorithm(
 AlgorithmType.WCC,
 schema,
 satellite_collections=["your", "satellite", "collections"]
)
print(selection.excluded_vertices) # Should show satellites
```

### Issue: PageRank scores seem wrong

**Problem**: Important entities have low PageRank

**Solution**: May be excluding relevant collections. Verify:

```python
selection = select_collections_for_algorithm(
 AlgorithmType.PAGERANK,
 schema,
 satellite_collections=["metadata"]
)
print(selection.vertex_collections) # Should be comprehensive
```

### Issue: Auto-classification is incorrect

**Problem**: Core collection classified as satellite

**Solution**: Provide explicit hints:

```python
# Override auto-classification
generator = TemplateGenerator(
 graph_name="my_graph",
 core_collections=["important_collection"], # Force as core
 satellite_collections=["reference_data"]
)
```

## Summary

The Collection Selection Agent ensures that:

1. **WCC/SCC** focus on core graph structure (exclude satellites)
2. **PageRank/Betweenness** use the full graph (include everything)
3. **Label Propagation** focuses on communities (core + bridges)
4. Selection reasoning is transparent and documented in template metadata
5. You can provide hints or let the system auto-classify

This results in more accurate algorithm results and better performance.

