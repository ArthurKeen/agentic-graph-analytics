# Interactive Report Generation with Charts

**Feature Status**: Implemented 
**Version**: 1.1.0 
**Requirements**: `plotly` (optional, for charts)

---

## Overview

The Graph Analytics AI Platform now generates **beautiful, interactive HTML reports** with embedded Plotly charts. Reports include:

- **Interactive visualizations** (hover, zoom, pan)
- **AI-generated insights** with confidence scores
- **Actionable recommendations** prioritized by impact
- **Algorithm-specific charts** tailored to each analysis type
- **Professional design** ready for stakeholder presentations

---

## Installation

### Basic Installation (Markdown reports only)
```bash
pip install graph-analytics-ai
```

### With Chart Generation
```bash
pip install graph-analytics-ai plotly
```

---

## Quick Start

### Generate HTML Report with Charts

```python
from graph_analytics_ai.ai.reporting import ReportGenerator, HTMLReportFormatter

# Initialize with chart generation enabled
generator = ReportGenerator(enable_charts=True)

# Generate report from execution results
report = generator.generate_report(execution_result, context={
 "use_case": {"title": "Household Identity Resolution"},
 "requirements": {"domain": "advertising technology"}
})

# Format as interactive HTML
html_formatter = HTMLReportFormatter()
charts = report.metadata.get('charts', {})
html_content = html_formatter.format_report(report, charts=charts)

# Save to file
with open('report.html', 'w') as f:
 f.write(html_content)
```

### Result
 Interactive HTML file with embedded Plotly charts 
 No external dependencies (charts embedded in HTML) 
 Works offline, shareable via email

---

## Algorithm-Specific Charts

Each algorithm gets tailored visualizations:

### PageRank Analysis

**Charts Generated:**
1. **Top Influencers Bar Chart**
 - Shows top 20 nodes by PageRank score
 - Hover to see exact scores
 - Color-coded by influence level

2. **Rank Distribution Histogram**
 - Log-scale distribution of all ranks
 - Identifies power-law patterns
 - Highlights concentration

3. **Cumulative Influence**
 - Shows % of total influence by top N nodes
 - "80/20 rule" visualization
 - Helps identify critical nodes

**Example Output:**
```
Top 10 nodes control 82% of network influence
```

### WCC (Weakly Connected Components)

**Charts Generated:**
1. **Top 10 Largest Components**
 - Bar chart of component sizes
 - Shows node counts per component
 - Identifies main cluster

2. **Component Size Distribution**
 - Histogram of all component sizes
 - Log-scale for skewed distributions
 - Reveals fragmentation patterns

3. **Connectivity Overview (Pie Chart)**
 - Donut chart showing cluster breakdown
 - Main cluster vs. others
 - Total component count in center

**Example Output:**
```
4,534 distinct components identified
Main cluster: 155,131 nodes (97.43%)
```

### Betweenness Centrality

**Charts Generated:**
1. **Top Bridge Nodes**
 - Bar chart of highest betweenness scores
 - Identifies critical connection points
 - Highlights network bottlenecks

2. **Betweenness Distribution**
 - Histogram of all betweenness values
 - Log-scale for highly skewed data
 - Shows bridge node rarity

**Example Output:**
```
7 critical bridge nodes connect all major clusters
```

### Label Propagation (Community Detection)

**Charts Generated:**
1. **Top 10 Communities**
 - Bar chart of largest communities
 - Member counts per community
 - Community distribution

2. **Community Size Distribution**
 - Histogram of all community sizes
 - Reveals clustering patterns
 - Identifies dominant communities

**Example Output:**
```
12 major communities detected
Largest community: 45,000 members
```

### SCC (Strongly Connected Components)

**Charts Generated:**
- Same as WCC, with SCC-specific context
- Emphasizes bidirectional relationships
- Highlights cycle detection

---

## Report Structure

### 1. Executive Summary
- Algorithm and key metrics
- Total results processed
- Execution time
- Number of insights generated

### 2. Interactive Charts
- Algorithm-specific visualizations
- Embedded Plotly charts
- Fully interactive (hover, zoom, pan)

### 3. Key Insights
- AI-generated findings
- Confidence scores (0-100%)
- Business impact statements
- Color-coded by confidence level

### 4. Recommendations
- Prioritized action items
- High/Medium/Low priority
- Expected business impact
- Effort estimation

### 5. Detailed Metrics
- Complete execution statistics
- Dataset information
- Algorithm-specific metrics

---

## Customization

### Theme Selection

```python
from graph_analytics_ai.ai.reporting import HTMLReportFormatter

# Modern theme (default)
formatter = HTMLReportFormatter(theme="modern")

# Classic theme
formatter = HTMLReportFormatter(theme="classic")

# Dark theme
formatter = HTMLReportFormatter(theme="dark")
```

### Chart Customization

```python
from graph_analytics_ai.ai.reporting import ChartGenerator

# Initialize with custom theme
chart_gen = ChartGenerator(theme="plotly_dark")

# Generate specific chart type
charts = chart_gen.generate_wcc_charts(results, top_n=20) # Show top 20 instead of 10
```

### Disable Charts

```python
# Generate markdown report without charts
generator = ReportGenerator(enable_charts=False)
report = generator.generate_report(execution_result)
markdown = generator.format_report(report, ReportFormat.MARKDOWN)
```

---

## Integration with Workflow

### Agentic Workflow with Charts

```python
from graph_analytics_ai.ai.agents import AgenticWorkflowRunner

# Run workflow with chart generation enabled
runner = AgenticWorkflowRunner(
 db_connection=db,
 llm_provider=llm,
 core_collections=["Device", "IP", "AppProduct"],
 satellite_collections=["Publisher", "Location"],
 enable_tracing=True
)

result = runner.run(
 use_case_file="use_cases.md",
 output_dir="./workflow_output"
)

# Reports automatically generated with charts
# Located in: ./workflow_output/reports/*.html
```

### Manual Report Generation

```python
from graph_analytics_ai.ai.execution import AnalysisExecutor
from graph_analytics_ai.ai.reporting import ReportGenerator, HTMLReportFormatter

# Execute analysis
executor = AnalysisExecutor()
execution_result = executor.execute_template(template, wait=True)

# Generate report with charts
generator = ReportGenerator(enable_charts=True)
report = generator.generate_report(execution_result, context={
 "use_case": {"title": "My Analysis"},
 "requirements": {"domain": "my domain"}
})

# Save as HTML
html_formatter = HTMLReportFormatter()
charts = report.metadata.get('charts', {})
html_content = html_formatter.format_report(report, charts=charts)

with open('my_report.html', 'w') as f:
 f.write(html_content)
```

---

## Chart Features

### Interactive Features

All charts include:
- **Hover tooltips** - Detailed information on hover
- **Zoom & Pan** - Explore data interactively
- **Download** - Export as PNG (Plotly toolbar)
- **Responsive** - Works on mobile/tablet/desktop
- **Offline** - No internet required after generation

### Performance

- **Fast generation**: ~1-2 seconds for 100K+ results
- **Small file size**: ~500KB for full HTML report with 3 charts
- **Browser compatibility**: All modern browsers (Chrome, Firefox, Safari, Edge)

---

## Example: Household Identity Analysis

```python
# Generate household identity resolution report
from graph_analytics_ai.ai.reporting import ReportGenerator, HTMLReportFormatter

generator = ReportGenerator(enable_charts=True, use_llm_interpretation=False)

report = generator.generate_report(
 wcc_execution_result,
 context={
 "use_case": {
 "title": "Household Identity Resolution",
 "objective": "Group 159K devices into distinct household clusters"
 },
 "requirements": {
 "domain": "advertising technology",
 "objectives": [{
 "title": "Cross-Device Attribution",
 "success_criteria": [
 "Identify 1000+ distinct household clusters",
 "Main cluster < 98% of total devices"
 ]
 }]
 }
 }
)

# Format and save
html_formatter = HTMLReportFormatter()
charts = report.metadata.get('charts', {})
html_content = html_formatter.format_report(report, charts=charts)

with open('household_identity_report.html', 'w') as f:
 f.write(html_content)

print(f" Report generated: 4,534 households identified")
print(f" Charts: Component distribution, top clusters, connectivity")
print(f" Insights: {len(report.insights)} AI-generated findings")
```

**Output**: Interactive HTML report showing:
- 4,534 distinct household clusters
- 155,131 devices in main cluster (97.43%)
- Top 10 largest households
- Component size distribution histogram
- Connectivity pie chart
- 5+ actionable insights with confidence scores

---

## Troubleshooting

### Charts Not Generating

**Issue**: Reports have no charts

**Solution**:
```bash
# Check if plotly is installed
python -c "import plotly; print('Plotly installed')"

# If not, install it
pip install plotly

# Verify in code
from graph_analytics_ai.ai.reporting import is_plotly_available
print(is_plotly_available()) # Should print True
```

### Large File Size

**Issue**: HTML file is too large (>10MB)

**Solution**:
```python
# Limit chart data points
generator = ReportGenerator(enable_charts=True)

# Manually generate charts with limits
from graph_analytics_ai.ai.reporting import ChartGenerator
chart_gen = ChartGenerator()

# Show top 10 instead of top 20
charts = chart_gen.generate_pagerank_charts(results[:1000], top_n=10)
```

### Charts Not Interactive

**Issue**: Charts appear as static images

**Solution**: Ensure you're opening the HTML file in a browser (not a text editor)
```bash
# macOS
open report.html

# Linux
xdg-open report.html

# Windows
start report.html
```

---

## API Reference

### ReportGenerator

```python
class ReportGenerator:
 def __init__(
 self,
 llm_provider: Optional[LLMProvider] = None,
 use_llm_interpretation: bool = True,
 enable_charts: bool = True # NEW: Enable chart generation
 )
```

### ChartGenerator

```python
class ChartGenerator:
 def generate_pagerank_charts(results, top_n=20) -> Dict[str, str]
 def generate_wcc_charts(results, top_n=10) -> Dict[str, str]
 def generate_betweenness_charts(results, top_n=20) -> Dict[str, str]
 def generate_label_propagation_charts(results, top_n=10) -> Dict[str, str]
 def generate_scc_charts(results, top_n=10) -> Dict[str, str]
```

### HTMLReportFormatter

```python
class HTMLReportFormatter:
 def __init__(theme: str = "modern")
 def format_report(
 report: AnalysisReport,
 charts: Optional[Dict[str, str]] = None,
 include_raw_data: bool = False
 ) -> str
```

---

## What's Next?

### Future Enhancements (Planned)

1. **PDF Export** - Convert HTML reports to PDF
2. **More Chart Types** - Network graphs, heatmaps, sankey diagrams
3. **Custom Templates** - User-defined HTML templates
4. **Dashboard View** - Multi-report dashboard
5. **Real-time Updates** - Live chart updates during execution

### Feedback Welcome!

Have suggestions for chart improvements? Let us know!

---

## Related Documentation

- [Execution Reporting Guide](EXECUTION_REPORTING_GUIDE.md)
- [Report Generation Guide](../README.md#reporting)
- [Agentic Workflow Guide](../docs/WORKFLOW_TRACING_GUIDE.md)
- [Customer Project Instructions](../docs/CUSTOMER_PROJECT_INSTRUCTIONS.md)

---

**Generated**: December 22, 2025 
**Version**: 1.1.0 
**Status**: Production Ready 

