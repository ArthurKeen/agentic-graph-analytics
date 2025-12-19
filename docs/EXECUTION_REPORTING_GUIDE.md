# Execution Reporting Guide

## Overview

The Graph Analytics AI Platform now includes comprehensive execution reporting that captures detailed metrics about GAE algorithm execution, including timing breakdowns, cost analysis, and performance statistics.

## Features

### Automatic Metrics Collection
- **Phase-level timing**: Deploy, Load, Execute, Store
- **Cost tracking**: Engine deployment and runtime costs (AMP only)
- **Performance metrics**: Throughput calculations (vertices/sec, edges/sec)
- **Error tracking**: Detailed error logs per algorithm
- **Success rates**: Track success/failure across multiple executions

### Professional Reports
- **Markdown format**: Human-readable reports with tables and charts
- **Configurable sections**: Choose what to include in reports
- **Multiple output formats**: Markdown, JSON, HTML (coming soon)
- **Visual elements**: ASCII bar charts for timing distribution

## Quick Start

### Basic Usage

```python
from graph_analytics_ai import GAEOrchestrator
from graph_analytics_ai.ai.execution.metrics import ExecutionSummary, TimingBreakdown
from graph_analytics_ai.ai.reporting import ExecutionReportFormatter, ReportConfig

# Run GAE analysis (automatically tracks metrics)
orchestrator = GAEOrchestrator()
result = orchestrator.run_analysis(config)

# Create execution summary
summary = ExecutionSummary(
    workflow_id="my_workflow_001",
    started_at=result.start_time,
    completed_at=result.end_time,
    templates_executed=1,
    templates_succeeded=1 if result.status == "completed" else 0
)

# Add timing breakdown
summary.timing_breakdown = TimingBreakdown(
    graph_load_seconds=result.load_time_seconds,
    algorithm_execution_seconds=result.execution_time_seconds,
    results_store_seconds=result.store_time_seconds,
    total_seconds=result.duration_seconds
)

# Generate report
formatter = ExecutionReportFormatter()
report_md = formatter.format_report(summary)

# Save to file
from pathlib import Path
Path("execution_report.md").write_text(report_md)
```

### Configurable Reports

```python
from graph_analytics_ai.ai.reporting import ReportConfig, ReportSection

# Minimal executive summary only
minimal_config = ReportConfig(
    include_sections=[ReportSection.EXECUTIVE_SUMMARY],
    include_costs=False
)

# Full detailed report
detailed_config = ReportConfig(
    include_all_sections=True,
    include_detailed_timing=True,
    include_error_details=True,
    include_raw_metrics=True
)

# Cost-focused report for stakeholders
cost_config = ReportConfig(
    include_sections=[
        ReportSection.EXECUTIVE_SUMMARY,
        ReportSection.COST_ANALYSIS
    ],
    include_costs=True
)

formatter = ExecutionReportFormatter(cost_config)
report = formatter.format_report(summary)
```

## Report Sections

### Executive Summary
- Overall status (✅ success / ⚠️ partial / ❌ failed)
- Success rate percentage
- Total duration and cost
- Quick stats (vertices, edges, results processed)

### Timing Breakdown
- Phase-by-phase timing table
- Percentage distribution
- ASCII bar chart visualization

Example:
```
| Phase | Duration | Percentage |
|-------|----------|------------|
| Graph Loading | 12.5s | 9.8% |
| Algorithm Execution | 98.3s | 77.2% |
| Results Storage | 16.5s | 13.0% |
```

### Cost Analysis (AMP Only)
- Engine deployment cost
- Runtime cost by duration
- Cost per minute calculation
- Total estimated cost in USD

### Performance Metrics
- Total vertices/edges/results processed
- Throughput calculations (vertices/sec, edges/sec)
- Success/failure counts
- Aggregated statistics

### Algorithm Details
- Per-algorithm execution table
- Status indicators (✅/❌)
- Execution time
- Resource counts
- Retry attempts

### Error Log
- List of all errors encountered
- Algorithm-specific error messages
- Timestamp and context

### Raw Metrics (Optional)
- Complete JSON dump of all metrics
- For programmatic analysis or debugging

## Advanced Usage

### Aggregating Multiple Executions

```python
from datetime import datetime

# Create summary for multiple algorithms
summary = ExecutionSummary(
    workflow_id="batch_analysis_001",
    started_at=datetime.now(),
    templates_executed=5
)

# Add stats for each algorithm
for result in algorithm_results:
    summary.add_algorithm_stats(AlgorithmExecutionStats(
        algorithm=result.algorithm,
        job_id=result.job_id,
        execution_time_seconds=result.execution_time_seconds,
        vertex_count=result.vertex_count,
        edge_count=result.edge_count,
        results_count=result.documents_updated,
        status="completed" if result.status == AnalysisStatus.COMPLETED else "failed",
        error_message=result.error_message if result.status != AnalysisStatus.COMPLETED else None
    ))

# Automatically calculates aggregates
print(f"Success rate: {summary.success_rate}%")
print(f"Total execution time: {summary.total_execution_time_seconds}s")
print(f"Total vertices: {summary.total_vertices_processed:,}")
```

### Custom Report Formatting

```python
# Customize decimal places and visibility options
custom_config = ReportConfig(
    include_sections=[
        ReportSection.EXECUTIVE_SUMMARY,
        ReportSection.TIMING_BREAKDOWN,
        ReportSection.PERFORMANCE_METRICS
    ],
    decimal_places=4,  # More precision
    show_timestamps=True,
    show_percentages=True,
    max_algorithm_details=20  # Show more algorithms
)

formatter = ExecutionReportFormatter(custom_config)
```

### Workflow Integration

```python
from graph_analytics_ai.ai.workflow import WorkflowOrchestrator
from graph_analytics_ai.ai.reporting.config import WorkflowReportConfig

# Configure reporting for workflow
report_config = WorkflowReportConfig(
    enable_execution_reporting=True,
    execution_report=ReportConfig(
        include_all_sections=True
    )
)

# Initialize with report config
orchestrator = WorkflowOrchestrator(
    output_dir="./outputs",
    report_config=report_config
)

# Reports will be generated automatically in outputs/reports/
result = orchestrator.run_complete_workflow(...)

if result.execution_report_path:
    print(f"Execution report: {result.execution_report_path}")
```

## Metrics Reference

### TimingBreakdown

| Field | Type | Description |
|-------|------|-------------|
| `graph_load_seconds` | float | Time to load graph into GAE |
| `algorithm_execution_seconds` | float | Time to execute algorithm |
| `results_store_seconds` | float | Time to store results to database |
| `total_seconds` | float | Total execution time |
| `load_percentage` | float | % of time spent loading (calculated) |
| `execution_percentage` | float | % of time executing (calculated) |
| `storage_percentage` | float | % of time storing (calculated) |

### CostBreakdown

| Field | Type | Description |
|-------|------|-------------|
| `engine_deployment_cost_usd` | float | Cost to deploy engine |
| `runtime_cost_usd` | float | Cost of engine runtime |
| `storage_cost_usd` | float | Cost of data storage (if applicable) |
| `total_cost_usd` | float | Total estimated cost |
| `runtime_minutes` | float | Total runtime in minutes |
| `engine_size` | str | Engine size used (e.g., "e8") |

### AlgorithmExecutionStats

| Field | Type | Description |
|-------|------|-------------|
| `algorithm` | str | Algorithm name |
| `job_id` | str | GAE job ID |
| `execution_time_seconds` | float | Algorithm execution time |
| `vertex_count` | int | Number of vertices processed |
| `edge_count` | int | Number of edges processed |
| `results_count` | int | Number of results generated |
| `status` | str | Execution status ("completed", "failed") |
| `error_message` | str | Error message if failed |
| `retry_count` | int | Number of retry attempts |

### ExecutionSummary

| Field | Type | Description |
|-------|------|-------------|
| `workflow_id` | str | Unique workflow identifier |
| `started_at` | datetime | When execution started |
| `completed_at` | datetime | When execution completed |
| `templates_generated` | int | Number of templates generated |
| `templates_executed` | int | Number of templates executed |
| `templates_succeeded` | int | Number of successful executions |
| `templates_failed` | int | Number of failed executions |
| `success_rate` | float | Success rate percentage (calculated) |
| `total_execution_time_seconds` | float | Total execution time |
| `total_duration_seconds` | float | Total workflow duration (calculated) |
| `timing_breakdown` | TimingBreakdown | Detailed timing breakdown |
| `cost_breakdown` | CostBreakdown | Cost analysis (AMP only) |
| `algorithm_stats` | Dict | Per-algorithm statistics |
| `total_vertices_processed` | int | Total vertices across all executions |
| `total_edges_processed` | int | Total edges across all executions |
| `total_results_generated` | int | Total results across all executions |
| `engine_size` | str | Engine size used |
| `deployment_mode` | str | Deployment mode (AMP/self-managed) |
| `errors` | List[str] | List of errors encountered |
| `metadata` | Dict | Additional metadata |

## Examples

### Example 1: Single Algorithm Report

```python
from datetime import datetime
from graph_analytics_ai.ai.execution.metrics import ExecutionSummary, AlgorithmExecutionStats
from graph_analytics_ai.ai.reporting import ExecutionReportFormatter

# Create summary
summary = ExecutionSummary(
    workflow_id="pagerank_analysis_001",
    started_at=datetime(2025, 12, 18, 10, 0, 0),
    completed_at=datetime(2025, 12, 18, 10, 2, 15),
    templates_executed=1,
    templates_succeeded=1
)

# Add algorithm stats
summary.add_algorithm_stats(AlgorithmExecutionStats(
    algorithm="pagerank",
    job_id="job_abc123",
    execution_time_seconds=125.3,
    vertex_count=15234,
    edge_count=45891,
    results_count=15234,
    status="completed"
))

# Generate report
formatter = ExecutionReportFormatter()
report = formatter.format_report(summary)
print(report)
```

### Example 2: Batch Analysis Report

```python
# Multiple algorithms with cost tracking
summary = ExecutionSummary(
    workflow_id="batch_analysis_001",
    started_at=datetime(2025, 12, 18, 10, 0, 0),
    completed_at=datetime(2025, 12, 18, 10, 15, 30),
    templates_executed=3,
    templates_succeeded=3,
    engine_size="e16",
    deployment_mode="amp"
)

# Add cost breakdown
summary.cost_breakdown = CostBreakdown(
    engine_deployment_cost_usd=0.0050,
    runtime_cost_usd=0.0823,
    total_cost_usd=0.0873,
    runtime_minutes=15.5,
    engine_size="e16"
)

# Add multiple algorithm stats
for algo in ["pagerank", "wcc", "label_propagation"]:
    summary.add_algorithm_stats(AlgorithmExecutionStats(
        algorithm=algo,
        execution_time_seconds=300.0,
        vertex_count=15234,
        edge_count=45891,
        results_count=15234,
        status="completed"
    ))

# Generate detailed report
config = ReportConfig(include_all_sections=True)
formatter = ExecutionReportFormatter(config)
report = formatter.format_report(summary)

# Save to file
from pathlib import Path
Path("batch_analysis_report.md").write_text(report)
```

## Best Practices

### 1. Always Track Metrics
Enable metric tracking for all production executions to maintain audit trails and performance history.

### 2. Choose Appropriate Detail Levels
- **Executive summaries** for stakeholders
- **Detailed reports** for operations teams
- **Raw metrics** for debugging

### 3. Archive Reports
Save reports for historical analysis and trend tracking.

### 4. Monitor Costs
Regularly review cost breakdowns to optimize engine usage and spending.

### 5. Track Error Patterns
Use error logs to identify and fix recurring issues.

## Troubleshooting

### Report Generation Fails

**Problem**: `_generate_execution_report()` returns None

**Solutions**:
- Check `report_config.enable_execution_reporting` is True
- Verify output directory permissions
- Check for exceptions in logs

### Missing Metrics

**Problem**: Timing breakdown shows zeros

**Solutions**:
- Ensure GAEOrchestrator is tracking phases
- Check that `AnalysisResult` has timing fields populated
- Verify execution completed successfully

### Cost Tracking Not Working

**Problem**: `cost_breakdown` is None

**Solutions**:
- Cost tracking only works for AMP deployments
- Verify `GAE_DEPLOYMENT_MODE=amp` in environment
- Check engine size is recognized

## API Reference

See module docstrings for complete API documentation:
- `graph_analytics_ai.ai.execution.metrics`
- `graph_analytics_ai.ai.reporting.config`
- `graph_analytics_ai.ai.reporting.formatter`

## Related Documentation

- [Testing and Reporting Analysis](../TESTING_AND_REPORTING_ANALYSIS.md)
- [Implementation Summary](../IMPLEMENTATION_SUMMARY.md)
- [Integration Tests](../tests/integration/README.md)

---

**Version:** 1.0.0  
**Last Updated:** December 18, 2025  
**Status:** Production Ready

