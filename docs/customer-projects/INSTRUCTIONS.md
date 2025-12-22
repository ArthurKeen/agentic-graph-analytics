# Instructions for Projects Using graph-analytics-ai-platform

## For Customer Projects (e.g., premion-graph-analytics)

This guide explains how to use the latest features in your project that imports the `graph-analytics-ai-platform` library.

**New Features** ✨:
- **Interactive HTML Reports with Plotly Charts** - Beautiful visualizations for your analysis results
- **Collection Selection** - Intelligent selection of graph collections for different algorithms

---

## 🎨 NEW: Interactive HTML Reports with Charts

### What's New

Your analysis reports can now include **interactive Plotly charts**:
- Bar charts of top results (influencers, components, communities)
- Distribution histograms (log-scale for skewed data)
- Pie/donut charts for connectivity overview
- Hover tooltips, zoom, pan controls
- Professional gradient design

### Quick Start with Charts

```bash
# Install Plotly (one-time)
pip install plotly
```

```python
from graph_analytics_ai.ai.reporting import ReportGenerator, HTMLReportFormatter

# Generate report with interactive charts (enabled by default)
generator = ReportGenerator(enable_charts=True)
report = generator.generate_report(execution_result, context={
    "use_case": {"title": "Your Analysis Name"},
    "requirements": {"domain": "your domain"}
})

# Format as HTML
formatter = HTMLReportFormatter()
charts = report.metadata.get('charts', {})
html_content = formatter.format_report(report, charts=charts)

# Save
with open('report.html', 'w') as f:
    f.write(html_content)

print(f"✅ Generated report with {len(charts)} interactive charts!")
```

### What Charts Are Generated

| Algorithm | Charts |
|-----------|--------|
| **PageRank** | Top influencers bar chart, distribution histogram, cumulative influence |
| **WCC** | Top components bar chart, size distribution, connectivity pie chart |
| **Betweenness** | Top bridge nodes, centrality distribution |
| **Label Propagation** | Top communities, community size distribution |
| **SCC** | Same as WCC |

### Example: Household Analysis Charts

For Premion household identity resolution (WCC):

```python
# Your existing workflow automatically generates charts
generator = ReportGenerator(enable_charts=True)
report = generator.generate_report(wcc_execution_result, context={
    "use_case": {"title": "Household Identity Resolution"},
    "requirements": {"domain": "advertising technology"}
})

# Get charts
formatter = HTMLReportFormatter()
charts = report.metadata.get('charts', {})
html = formatter.format_report(report, charts=charts)

with open('household_analysis_report.html', 'w') as f:
    f.write(html)

# Result: 3 interactive charts showing:
# 1. Top 10 largest household clusters (bar chart)
# 2. Household size distribution (histogram)
# 3. Network connectivity overview (pie chart)
```

### Chart Features

✅ **Interactive** - Hover for exact values, zoom to explore, pan to navigate  
✅ **Professional** - Modern gradient design, color-coded  
✅ **Exportable** - Download charts as PNG for presentations  
✅ **Responsive** - Works on desktop, tablet, mobile  
✅ **Print-Friendly** - Formatted for PDF export  
✅ **Offline** - No internet required after generation  

### Disabling Charts

If you don't want charts (e.g., automated pipelines):

```python
# Generate markdown reports only
generator = ReportGenerator(enable_charts=False)
```

### More Information

- **Full Guide**: See `docs/INTERACTIVE_REPORT_GENERATION.md` in the library repo
- **Quick Reference**: See `CHART_GENERATION_QUICK_START.md`
- **Example Code**: See `examples/chart_report_example.py`

---

## 📊 Collection Selection Feature

This guide also explains how to use the **Collection Selection** feature for intelligent collection filtering.

---

## Quick Start

### 1. Update Your Library Dependency

```bash
# In your customer project directory (e.g., ~/code/premion-graph-analytics)
cd ~/code/premion-graph-analytics

# If you installed the library in editable mode
cd ~/code/graph-analytics-ai-platform
git pull origin feature/ai-foundation-phase1

# The collection selection feature is now available
```

### 2. Specify Your Collection Roles

When initializing the workflow, specify which collections are satellites vs. core:

```python
from graph_analytics_ai.ai.templates import TemplateGenerator

# Initialize with your collection roles
generator = TemplateGenerator(
    graph_name="premion_media_graph",
    satellite_collections=[
        # Reference data, lookups, metadata
        "audience_metadata",
        "device_specs",
        "geo_lookups",
        "rate_cards",
        "configuration_settings"
    ],
    core_collections=[
        # Primary business entities
        "audiences",
        "campaigns",
        "creatives",
        "devices",
        "publishers",
        "placements"
    ]
)
```

### 3. Generate Templates

The collection selection happens automatically:

```python
# Generate templates for your use cases
templates = generator.generate_templates(use_cases, schema, schema_analysis)

# Each template now has appropriate collections selected
# - WCC excludes satellites (finds core components)
# - PageRank includes everything (full graph importance)
```

---

## Understanding Collection Roles

### Satellite Collections
Collections that should be **excluded** from connectivity algorithms (WCC, SCC):
- Reference tables (lookups, mappings)
- Metadata (tags, attributes, properties)
- Configuration data
- System settings
- Dimension tables with few relationships

**Examples**:
- `audience_metadata` - Descriptive info about audiences
- `device_specs` - Technical specifications
- `geo_lookups` - Geographic reference data
- `rate_cards` - Pricing information

### Core Collections
Collections that contain your **primary business entities**:
- Main transactional data
- Primary entities with rich relationships
- Collections central to your business logic

**Examples**:
- `audiences` - Actual audience entities
- `campaigns` - Marketing campaigns
- `devices` - Connected TV devices
- `publishers` - Content publishers

---

## What Happens Automatically

### WCC (Weakly Connected Components)
```python
# Automatically excludes satellites
# Input: audiences, campaigns, devices, audience_metadata, device_specs
# WCC uses: audiences, campaigns, devices (core only)
# Result: Meaningful components in your business graph
```

### SCC (Strongly Connected Components)
```python
# Automatically excludes satellites
# Same behavior as WCC but for directed, strongly connected components
```

### PageRank
```python
# Automatically includes everything
# Input: audiences, campaigns, devices, audience_metadata, device_specs
# PageRank uses: ALL collections
# Result: Accurate importance scores across full graph
```

### Betweenness Centrality
```python
# Automatically includes everything
# Needs full graph for accurate centrality measures
```

### Label Propagation
```python
# Automatically excludes satellites
# Focuses on community detection in core graph
```

---

## Integration Patterns

### Pattern 1: Direct Template Generation (Recommended)

```python
from graph_analytics_ai.ai.templates import TemplateGenerator

# 1. Define collection roles
generator = TemplateGenerator(
    graph_name="your_graph",
    satellite_collections=["metadata", "configs"],
    core_collections=["entities", "relationships"]
)

# 2. Generate templates
templates = generator.generate_templates(use_cases, schema)

# 3. Review selections before execution
for template in templates:
    algo = template.algorithm.algorithm.value
    colls = template.config.vertex_collections
    reasoning = template.metadata.get('collection_selection_reasoning', 'N/A')
    
    print(f"\n{template.name}")
    print(f"  Algorithm: {algo}")
    print(f"  Collections: {colls}")
    print(f"  Reasoning: {reasoning}")
    
    # Check for exclusions
    excluded = template.metadata.get('excluded_collections', {})
    if excluded.get('vertices'):
        print(f"  Excluded: {excluded['vertices']}")
```

### Pattern 2: Testing Selections First

```python
from graph_analytics_ai.ai.templates import select_collections_for_algorithm, AlgorithmType

# Before running expensive analyses, test what will be selected
wcc_selection = select_collections_for_algorithm(
    algorithm=AlgorithmType.WCC,
    schema=your_schema,
    satellite_collections=["audience_metadata", "device_specs"],
    core_collections=["audiences", "campaigns"]
)

print(f"WCC will use: {wcc_selection.vertex_collections}")
print(f"WCC will exclude: {wcc_selection.excluded_vertices}")
print(f"Reasoning: {wcc_selection.reasoning}")
print(f"Estimated size: {wcc_selection.estimated_graph_size}")

# If selection looks good, proceed with template generation
```

### Pattern 3: Workflow Integration

If your workflow uses `WorkflowOrchestrator`:

```python
from graph_analytics_ai.ai.workflow import WorkflowOrchestrator
from graph_analytics_ai.ai.templates import TemplateGenerator

# Create configured generator
generator = TemplateGenerator(
    graph_name="your_graph",
    satellite_collections=["metadata"],
    core_collections=["entities"]
)

# Pass to workflow if it accepts a template_generator parameter
# (Check WorkflowOrchestrator API - this may vary)
orchestrator = WorkflowOrchestrator(
    graph_name="your_graph",
    template_generator=generator  # If supported
)

# Or generate templates separately and pass them in
templates = generator.generate_templates(use_cases, schema)
# ... use templates in your workflow
```

---

## How to Identify Your Collection Roles

### Method 1: By Purpose

Ask yourself:
- **Is this collection a reference/lookup table?** → Satellite
- **Does this collection have few relationships?** → Satellite
- **Is this collection metadata about other entities?** → Satellite
- **Is this collection central to my business logic?** → Core
- **Does this collection have many relationships?** → Core

### Method 2: By Naming Conventions

Common satellite patterns:
- Contains `_metadata`, `_specs`, `_lookup`, `_reference`
- Contains `config`, `setting`, `dimension`
- Small tables (< 100 documents)

Common core patterns:
- Main business entity names (`customers`, `products`, `orders`)
- Large tables with many relationships
- Transaction or event collections

### Method 3: Test and Observe

```python
# Let it auto-classify first
generator = TemplateGenerator(graph_name="your_graph")
templates = generator.generate_templates(use_cases, schema)

# Review what was classified
for template in templates:
    if template.algorithm.algorithm == AlgorithmType.WCC:
        print(f"Auto-classified as core: {template.config.vertex_collections}")
        excluded = template.metadata.get('excluded_collections', {})
        if excluded.get('vertices'):
            print(f"Auto-classified as satellite: {excluded['vertices']}")

# Then explicitly configure based on what you observed
```

---

## Validation and Testing

### 1. Verify WCC Results

Compare WCC results with and without satellite exclusion:

```python
# Generate templates with satellite exclusion
generator_with_exclusion = TemplateGenerator(
    graph_name="your_graph",
    satellite_collections=["metadata", "configs"]
)
templates_excluded = generator_with_exclusion.generate_templates(use_cases, schema)

# Check what WCC will use
wcc_template = [t for t in templates_excluded if t.algorithm.algorithm == AlgorithmType.WCC][0]
print(f"WCC collections: {wcc_template.config.vertex_collections}")
print(f"Expected: Should NOT include 'metadata' or 'configs'")

# Run WCC and check component count
# - With exclusion: Fewer, more meaningful components
# - Without exclusion: Many tiny, false components
```

### 2. Verify PageRank Completeness

```python
# PageRank should use all collections
pr_template = [t for t in templates_excluded if t.algorithm.algorithm == AlgorithmType.PAGERANK][0]
all_collections = list(schema.vertex_collections.keys())

assert set(pr_template.config.vertex_collections) == set(all_collections), \
    "PageRank should include all collections"
print("✓ PageRank using full graph")
```

### 3. Review Selection Reasoning

```python
# Check that reasoning makes sense
for template in templates:
    reasoning = template.metadata.get('collection_selection_reasoning', '')
    print(f"\n{template.algorithm.algorithm.value}:")
    print(f"  {reasoning}")
    
    # Validate reasoning matches algorithm type
    if template.algorithm.algorithm in [AlgorithmType.WCC, AlgorithmType.SCC]:
        assert "core graph" in reasoning.lower() or "exclude" in reasoning.lower()
    elif template.algorithm.algorithm in [AlgorithmType.PAGERANK, AlgorithmType.BETWEENNESS_CENTRALITY]:
        assert "complete graph" in reasoning.lower() or "full graph" in reasoning.lower()
```

---

## Common Issues and Solutions

### Issue 1: WCC Finding Too Many Components

**Problem**: WCC is finding 100+ tiny components

**Cause**: Likely including satellite collections

**Solution**:
```python
# Explicitly exclude satellites
generator = TemplateGenerator(
    graph_name="your_graph",
    satellite_collections=["metadata", "configs", "lookups"]  # Add all satellites
)
```

### Issue 2: PageRank Scores Seem Wrong

**Problem**: Important entities have unexpectedly low PageRank

**Cause**: May be excluding relevant collections

**Solution**:
```python
# Verify PageRank is using full graph
pr_selection = select_collections_for_algorithm(
    AlgorithmType.PAGERANK,
    schema,
    satellite_collections=["metadata"]
)
print(f"PageRank collections: {pr_selection.vertex_collections}")
# Should be comprehensive
```

### Issue 3: Auto-Classification Is Wrong

**Problem**: System classifies a core collection as satellite

**Solution**:
```python
# Override with explicit core_collections
generator = TemplateGenerator(
    graph_name="your_graph",
    core_collections=["important_collection"],  # Force as core
    satellite_collections=["reference_data"]
)
```

### Issue 4: Don't Know Which Collections Are Satellites

**Solution**:
```python
# Start with auto-classification and review
generator = TemplateGenerator(graph_name="your_graph")
templates = generator.generate_templates(use_cases, schema)

# Check what was selected
wcc_templates = [t for t in templates if t.algorithm.algorithm == AlgorithmType.WCC]
for template in wcc_templates:
    print(f"Used: {template.config.vertex_collections}")
    excluded = template.metadata.get('excluded_collections', {})
    print(f"Excluded: {excluded.get('vertices', [])}")

# Use this to inform your explicit configuration
```

---

## Example: Complete Workflow

```python
from graph_analytics_ai.ai.schema import SchemaExtractor
from graph_analytics_ai.ai.generation import UseCaseGenerator
from graph_analytics_ai.ai.templates import TemplateGenerator, AlgorithmType

# 1. Extract schema
extractor = SchemaExtractor(db_connection)
schema = extractor.extract()

# 2. Generate use cases (from your requirements)
use_case_generator = UseCaseGenerator()
use_cases = use_case_generator.generate(requirements, schema)

# 3. Create template generator with collection roles
generator = TemplateGenerator(
    graph_name="premion_media_graph",
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

# 4. Generate templates (collection selection happens here)
templates = generator.generate_templates(use_cases, schema)

# 5. Review selections
print("\n=== Collection Selections ===")
for template in templates:
    print(f"\n{template.name}")
    print(f"  Algorithm: {template.algorithm.algorithm.value}")
    print(f"  Vertex Collections: {template.config.vertex_collections}")
    
    reasoning = template.metadata.get('collection_selection_reasoning', 'N/A')
    print(f"  Reasoning: {reasoning}")
    
    excluded = template.metadata.get('excluded_collections', {})
    if excluded.get('vertices'):
        print(f"  Excluded Vertices: {excluded['vertices']}")
    if excluded.get('edges'):
        print(f"  Excluded Edges: {excluded['edges']}")
    
    size = template.metadata.get('estimated_graph_size', {})
    if size:
        print(f"  Graph Size: {size.get('vertices', 0)} vertices, {size.get('edges', 0)} edges")

# 6. Execute templates
from graph_analytics_ai.ai.execution import AnalysisExecutor

executor = AnalysisExecutor(gae_connection)
results = []

for template in templates:
    print(f"\nExecuting: {template.name}")
    result = executor.execute(template)
    results.append(result)
    print(f"  Status: {result.status}")

# 7. Generate reports
from graph_analytics_ai.ai.reporting import ReportGenerator, HTMLReportFormatter

# Generate reports with interactive charts
report_gen = ReportGenerator(enable_charts=True)
reports = []

for result in results:
    report = report_gen.generate_report(result, context={
        "use_case": {"title": result.job.template_name},
        "requirements": {"domain": "your domain"}
    })
    reports.append(report)
    
    # Save as HTML with charts
    formatter = HTMLReportFormatter()
    charts = report.metadata.get('charts', {})
    html = formatter.format_report(report, charts=charts)
    
    filename = f"{result.job.template_name.replace(' ', '_')}_report.html"
    with open(filename, 'w') as f:
        f.write(html)
    
    print(f"  Saved: {filename} ({len(charts)} charts)")

print(f"\n✓ Generated {len(reports)} HTML reports with interactive charts")
```

---

## API Reference

### TemplateGenerator

```python
TemplateGenerator(
    graph_name: str,
    default_engine_size: EngineSize = EngineSize.SMALL,
    auto_optimize: bool = True,
    satellite_collections: Optional[List[str]] = None,  # NEW
    core_collections: Optional[List[str]] = None        # NEW
)
```

**New Parameters**:
- `satellite_collections`: List of collection names to exclude from connectivity algorithms (WCC, SCC)
- `core_collections`: List of collection names to prioritize as core entities

### select_collections_for_algorithm

```python
from graph_analytics_ai.ai.templates import select_collections_for_algorithm

selection = select_collections_for_algorithm(
    algorithm: AlgorithmType,
    schema: GraphSchema,
    satellite_collections: Optional[List[str]] = None,
    core_collections: Optional[List[str]] = None
) -> CollectionSelection
```

**Returns `CollectionSelection` with**:
- `vertex_collections`: List of selected vertex collections
- `edge_collections`: List of selected edge collections
- `excluded_vertices`: List of excluded vertices with reasons
- `excluded_edges`: List of excluded edges
- `reasoning`: Human-readable explanation
- `estimated_graph_size`: Dict with vertices/edges/collections counts

---

## Best Practices

1. **Always specify satellite collections explicitly** for production workflows
2. **Use auto-classification for exploration** and initial testing
3. **Review selection reasoning** before executing expensive GAE jobs
4. **Test WCC results** with and without satellite exclusion to verify improvement
5. **Document your collection roles** in your project's README
6. **Version control your collection configuration** (don't hardcode)

---

## Documentation References

- **User Guide**: `docs/COLLECTION_SELECTION_GUIDE.md` in the library repo
- **Implementation Details**: `docs/api-reference/COLLECTION_SELECTION_IMPLEMENTATION.md`
- **Unit Tests**: `tests/unit/ai/templates/test_collection_selector.py` (examples)

---

## Support

If collection selection isn't working as expected:
1. Review the reasoning in `template.metadata['collection_selection_reasoning']`
2. Check what was excluded in `template.metadata['excluded_collections']`
3. Test with `select_collections_for_algorithm()` to preview selections
4. Consult the full guide: `docs/COLLECTION_SELECTION_GUIDE.md`

