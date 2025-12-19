# Workflow Tracing and Observability Guide

## Overview

The **Workflow Tracing System** provides comprehensive observability for agentic workflows, allowing you to:

- 📊 **Track every event** in your workflow execution
- ⏱️ **Measure performance** of agents, LLM calls, and tools
- 💰 **Estimate costs** of LLM usage
- 🐛 **Debug issues** with detailed logging and state snapshots
- 📈 **Visualize** agent interactions and timeline
- 🔄 **Replay** past executions for analysis
- 📉 **Compare** different workflow runs

---

## Quick Start

### Enable Tracing

```python
from graph_analytics_ai.ai.agents import AgenticWorkflowRunner

# Enable tracing (default: enabled)
runner = AgenticWorkflowRunner(
    graph_name="my_graph",
    enable_tracing=True
)

state = runner.run()

# Print trace summary
runner.print_trace_summary()

# Export trace
runner.export_trace("./traces", formats=['all'])
```

### Basic Usage

```python
# Run workflow with tracing
runner = AgenticWorkflowRunner(graph_name="my_graph")
state = runner.run()

# Get trace
trace = runner.get_trace()

# Export in different formats
runner.export_trace("./traces", formats=['json', 'html', 'markdown'])
```

---

## Features

### 1. Real-Time Event Tracking

Every significant event is captured:

- Workflow start/end
- Agent invocations and completions
- LLM calls (timing, token usage)
- Tool invocations
- Message exchanges between agents
- Errors and exceptions
- Workflow step transitions

### 2. Performance Metrics

**Workflow-Level Metrics:**
- Total execution time
- Steps completed
- Average time per step
- Total LLM calls and tokens
- Estimated cost (USD)
- Message count
- Error count

**Agent-Level Metrics:**
- Invocation count
- Total/average execution time
- LLM usage (calls, tokens, time)
- Tool invocations
- Messages sent/received
- Error count

### 3. Export Formats

#### JSON (Machine-Readable)
```python
runner.export_trace("./traces", formats=['json'])
```

Complete trace data in JSON format for programmatic analysis.

#### HTML Timeline (Interactive)
```python
runner.export_trace("./traces", formats=['html'])
```

Beautiful interactive timeline with:
- Event filtering (all, agents, steps, errors)
- Performance metrics dashboard
- Color-coded event types
- Duration indicators

#### SVG Diagram (Agent Interactions)
```python
runner.export_trace("./traces", formats=['svg'])
```

Visual diagram showing message flow between agents.

#### Markdown Report
```python
runner.export_trace("./traces", formats=['markdown'])
```

Human-readable report with:
- Performance summary
- Slowest agents
- Top LLM consumers
- Event timeline
- Agent interactions

### 4. Debug Mode

Enable verbose logging and state snapshots:

```python
runner = AgenticWorkflowRunner(
    graph_name="my_graph",
    enable_tracing=True,
    enable_debug_mode=True  # Verbose logging
)

state = runner.run()

# Debug log is automatically exported with trace
runner.export_trace("./traces")
```

Debug mode provides:
- Detailed log messages from each agent
- State snapshots at regular intervals
- Step-by-step execution details
- Enhanced error diagnostics

### 5. Trace Replay

Load and analyze saved traces:

```python
from graph_analytics_ai.ai.tracing.replay import TraceReplayer

# Load trace
replayer = TraceReplayer("./traces/trace_123.json")

# Print summary
replayer.print_summary()

# Replay events (with adjustable speed)
replayer.replay_timeline(speed=2.0)  # 2x speed

# Find bottlenecks
bottlenecks = replayer.find_bottlenecks(threshold_ms=1000)
for bottleneck in bottlenecks:
    print(f"{bottleneck['agent']}: {bottleneck['duration_ms']}ms")

# Analyze agent communication
comm_analysis = replayer.analyze_agent_communication()
print(f"Total messages: {comm_analysis['total_messages']}")
print(f"Most active pairs: {comm_analysis['most_active_pairs']}")
```

### 6. Trace Comparison

Compare two workflow runs:

```python
from graph_analytics_ai.ai.tracing.replay import compare_traces

comparison = compare_traces(
    "./traces/trace_old.json",
    "./traces/trace_new.json"
)

print(f"Time difference: {comparison['performance']['total_time_ms']['diff']}ms")
print(f"Token difference: {comparison['performance']['total_tokens']['diff']}")
print(f"Cost difference: ${comparison['performance']['cost']['diff']:.4f}")
```

---

## Usage Patterns

### Pattern 1: Basic Tracing

```python
# Simple workflow with tracing
runner = AgenticWorkflowRunner(graph_name="my_graph")
state = runner.run()

# View summary
runner.print_trace_summary()
```

### Pattern 2: Export and Analyze

```python
# Run workflow
runner = AgenticWorkflowRunner(graph_name="my_graph")
state = runner.run()

# Export all formats
runner.export_trace("./workflow_traces")

# Outputs:
# - trace_{id}.json              (complete data)
# - trace_{id}_timeline.html     (interactive timeline)
# - trace_{id}_agents.svg        (interaction diagram)
# - trace_{id}_report.md         (markdown report)
```

### Pattern 3: Debug Mode

```python
# Enable debug mode for troubleshooting
runner = AgenticWorkflowRunner(
    graph_name="my_graph",
    enable_tracing=True,
    enable_debug_mode=True
)

state = runner.run()

# Export with debug log
runner.export_trace("./debug_traces")

# Additional output:
# - debug_log_{trace_id}.json    (detailed debug log)
```

### Pattern 4: Performance Analysis

```python
# Run workflow
runner = AgenticWorkflowRunner(graph_name="my_graph")
state = runner.run()

# Get trace
trace = runner.get_trace()

# Analyze performance
if trace.performance:
    perf = trace.performance
    
    print("Slowest Agents:")
    for agent_info in perf.get_slowest_agents(5):
        print(f"  {agent_info['agent']}: {agent_info['total_time_ms']}ms")
    
    print("\nTop LLM Consumers:")
    for agent_info in perf.get_top_llm_consumers(5):
        print(f"  {agent_info['agent']}: {agent_info['total_tokens']} tokens")
    
    print(f"\nEstimated Cost: ${perf.llm_cost_estimate_usd:.4f}")
```

### Pattern 5: Replay and Investigation

```python
from graph_analytics_ai.ai.tracing.replay import TraceReplayer

# Load previous execution
replayer = TraceReplayer("./traces/trace_problematic_run.json")

# Find what took too long
bottlenecks = replayer.find_bottlenecks(threshold_ms=2000)
for b in bottlenecks:
    print(f"Slow operation: {b['agent']} - {b['event_type']}")
    print(f"  Duration: {b['duration_ms']}ms")
    print(f"  Data: {b['data']}")

# Analyze agent communication patterns
comm = replayer.analyze_agent_communication()
print(f"\nMost talkative agent pairs:")
for pair, count in comm['most_active_pairs'][:5]:
    print(f"  {pair}: {count} messages")
```

### Pattern 6: Continuous Monitoring

```python
import os
from datetime import datetime

def run_monitored_workflow(graph_name: str):
    """Run workflow with automatic trace export."""
    
    # Create timestamped trace directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_dir = f"./traces/{graph_name}/{timestamp}"
    
    # Run workflow
    runner = AgenticWorkflowRunner(
        graph_name=graph_name,
        enable_tracing=True
    )
    
    state = runner.run()
    
    # Export trace
    runner.export_trace(trace_dir, formats=['json', 'html', 'markdown'])
    
    # Print summary
    runner.print_trace_summary()
    
    # Check for issues
    trace = runner.get_trace()
    if trace.performance and trace.performance.total_errors > 0:
        print(f"\n⚠️  Warning: {trace.performance.total_errors} errors occurred")
    
    return state, trace_dir

# Use it
state, trace_dir = run_monitored_workflow("production_graph")
print(f"Trace saved to: {trace_dir}")
```

---

## Trace Data Model

### TraceEvent

Every event contains:

```python
{
    "event_id": "evt-123",
    "event_type": "agent_invoked",
    "timestamp": "2025-12-18T10:30:45.123Z",
    "agent_name": "SchemaAnalyst",
    "duration_ms": 1234.56,
    "data": {
        "key": "value",
        ...
    },
    "parent_event_id": "evt-122",  # For nested events
    "metadata": {}
}
```

### Event Types

- `workflow_start` / `workflow_end`
- `agent_invoked` / `agent_completed` / `agent_error`
- `message_sent` / `message_received`
- `llm_call_start` / `llm_call_end`
- `tool_invoked` / `tool_completed`
- `decision_made`
- `step_start` / `step_end`
- `state_snapshot`

### Performance Metrics

```python
{
    "workflow_id": "workflow-123",
    "total_time_ms": 45000,
    "steps_completed": 6,
    "total_llm_calls": 24,
    "total_llm_tokens": 125000,
    "estimated_cost_usd": 3.75,
    "total_messages": 18,
    "total_errors": 0,
    
    "agent_metrics": {
        "SchemaAnalyst": {
            "invocation_count": 1,
            "total_time_ms": 5000,
            "avg_time_ms": 5000,
            "llm_calls": 3,
            "total_tokens": 15000,
            ...
        },
        ...
    },
    
    "slowest_agents": [...],
    "top_llm_consumers": [...]
}
```

---

## Best Practices

### 1. Always Enable Tracing in Production

```python
# Enable tracing by default
runner = AgenticWorkflowRunner(
    graph_name="production_graph",
    enable_tracing=True  # Default, but explicit is better
)
```

**Benefits:**
- Performance insights
- Cost tracking
- Debugging historical issues
- Optimization opportunities

### 2. Use Debug Mode Selectively

```python
# Only enable for troubleshooting
enable_debug = os.getenv("DEBUG_MODE", "false").lower() == "true"

runner = AgenticWorkflowRunner(
    graph_name="my_graph",
    enable_debug_mode=enable_debug
)
```

**Reason:** Debug mode adds overhead and generates large logs.

### 3. Organize Traces by Date/Context

```python
from datetime import datetime

trace_dir = f"./traces/{graph_name}/{datetime.now().strftime('%Y-%m-%d')}"
runner.export_trace(trace_dir)
```

### 4. Monitor Performance Trends

```python
import json
from pathlib import Path

def collect_performance_metrics(traces_dir: str):
    """Collect metrics from all traces."""
    metrics = []
    
    for trace_file in Path(traces_dir).glob("**/trace_*.json"):
        with open(trace_file) as f:
            trace_data = json.load(f)
            if trace_data.get('performance'):
                metrics.append({
                    'trace_id': trace_data['trace_id'],
                    'total_time_ms': trace_data['performance']['total_time_ms'],
                    'llm_cost': trace_data['performance']['estimated_cost_usd'],
                    'errors': trace_data['performance']['total_errors']
                })
    
    return metrics

# Analyze trends
metrics = collect_performance_metrics("./traces")
avg_time = sum(m['total_time_ms'] for m in metrics) / len(metrics)
print(f"Average workflow time: {avg_time/1000:.2f}s")
```

### 5. Set Up Alerts for Anomalies

```python
def check_trace_health(trace):
    """Check if trace indicates issues."""
    issues = []
    
    if trace.performance:
        perf = trace.performance
        
        # Check for errors
        if perf.total_errors > 0:
            issues.append(f"Errors: {perf.total_errors}")
        
        # Check for slow execution
        if perf.total_time_ms > 60000:  # > 1 minute
            issues.append(f"Slow execution: {perf.total_time_ms/1000:.1f}s")
        
        # Check for high costs
        if perf.llm_cost_estimate_usd > 1.0:
            issues.append(f"High cost: ${perf.llm_cost_estimate_usd:.2f}")
    
    return issues

# Use it
trace = runner.get_trace()
issues = check_trace_health(trace)
if issues:
    print("⚠️  Issues detected:")
    for issue in issues:
        print(f"  - {issue}")
```

---

## API Reference

### AgenticWorkflowRunner

```python
AgenticWorkflowRunner(
    db_connection=None,
    llm_provider=None,
    graph_name: str = "graph",
    core_collections: Optional[List[str]] = None,
    satellite_collections: Optional[List[str]] = None,
    enable_tracing: bool = True,        # NEW
    enable_debug_mode: bool = False     # NEW
)
```

#### Methods

**`run(...) -> AgentState`**
Run workflow with tracing enabled.

**`get_trace() -> WorkflowTrace`**
Get finalized trace after workflow completion.

**`print_trace_summary()`**
Print formatted trace summary to console.

**`export_trace(output_dir: str, formats: Optional[List[str]] = None)`**
Export trace to specified formats.

- `formats`: List of `['json', 'html', 'svg', 'markdown', 'all']`
- Default: All formats

### TraceReplayer

```python
from graph_analytics_ai.ai.tracing.replay import TraceReplayer

replayer = TraceReplayer(trace_path="./traces/trace_123.json")
```

#### Methods

**`print_summary()`**
Print trace summary.

**`replay_timeline(speed: float = 1.0, filter_types: Optional[List[TraceEventType]] = None)`**
Replay events in chronological order.

**`find_bottlenecks(threshold_ms: float = 1000) -> List[Dict]`**
Find operations slower than threshold.

**`analyze_agent_communication() -> Dict`**
Analyze message flow between agents.

**`get_agent_timeline(agent_name: str) -> List[TraceEvent]`**
Get all events for a specific agent.

**`compare_with(other_trace_path: str) -> Dict`**
Compare with another trace.

### Utility Functions

```python
from graph_analytics_ai.ai.tracing.replay import load_trace, compare_traces
from graph_analytics_ai.ai.tracing.export import export_trace

# Load saved trace
trace = load_trace("./traces/trace_123.json")

# Compare two traces
comparison = compare_traces("trace1.json", "trace2.json")

# Export trace
export_trace(trace, output_dir="./output", formats=['html', 'json'])
```

---

## Troubleshooting

### Trace Not Generated

**Problem:** `get_trace()` returns `None`

**Solution:** Ensure tracing is enabled:
```python
runner = AgenticWorkflowRunner(enable_tracing=True)
```

### Large Trace Files

**Problem:** Trace JSON files are very large

**Solutions:**
1. Disable debug mode if not needed
2. Don't enable state snapshots for long workflows
3. Filter events when exporting

### Missing LLM Token Counts

**Problem:** Token counts show as 0

**Solution:** Token counts depend on LLM provider response. Some providers don't return token usage. Estimates are used when actual counts unavailable.

### Export Fails

**Problem:** `export_trace()` raises error

**Solution:** Ensure output directory is writable:
```python
from pathlib import Path
Path("./traces").mkdir(parents=True, exist_ok=True)
runner.export_trace("./traces")
```

---

## Examples

See `examples/tracing_demo.py` for complete examples of:
- Basic tracing usage
- Performance analysis
- Trace replay
- Comparison workflows
- Debug mode usage

---

## Performance Impact

Tracing overhead is minimal:
- **~2-5%** execution time overhead
- **~10-20 MB** memory per 1000 events
- **No impact** on workflow logic or results

Debug mode adds additional overhead:
- **~5-10%** execution time overhead
- Larger memory footprint due to state snapshots

**Recommendation:** Always enable tracing, only enable debug mode when needed.

---

## Summary

The tracing system provides comprehensive observability without significant overhead. Use it to:

1. ✅ **Monitor** production workflows
2. ✅ **Debug** issues with detailed logs
3. ✅ **Optimize** performance bottlenecks
4. ✅ **Track** LLM costs
5. ✅ **Analyze** agent interactions
6. ✅ **Compare** different runs

For questions or issues, see the [main documentation](../README.md) or [file an issue](https://github.com/ArthurKeen/graph-analytics-ai/issues).

