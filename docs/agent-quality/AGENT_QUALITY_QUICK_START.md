# Agent Quality Improvements - Quick Start Guide

This guide helps you use the new agent quality improvements in the Graph Analytics AI Platform.

## What Changed?

Reports now generate **3-5 specific, quantified insights** instead of 1 generic insight. Quality increased from ~75% to 90%+ relevance.

## No Action Required

Existing code automatically benefits from improvements. Just run your workflows as usual.

## Configuration Options

Control report quality vs. cost with environment variables.

### Option 1: High Quality (Recommended for Production)

```bash
export GAE_PLATFORM_USE_LLM_REPORTING=true
export GAE_PLATFORM_REPORTING_MIN_CONFIDENCE=0.5
```

**Benefits**: Best quality insights, 3-5 per report  
**Cost**: ~$0.17 per workflow

### Option 2: Cost Optimized

```bash
export GAE_PLATFORM_USE_LLM_REPORTING=false
```

**Benefits**: Faster, cheaper, still improved heuristics  
**Cost**: ~$0.05 per workflow  
**Quality**: 2-3 statistical insights per report

### Option 3: Maximum Quality (For Critical Reports)

```bash
export GAE_PLATFORM_USE_LLM_REPORTING=true
export GAE_PLATFORM_REPORTING_USE_REASONING=true
export GAE_PLATFORM_REPORTING_MIN_CONFIDENCE=0.7
```

**Benefits**: Chain-of-thought reasoning, highest quality  
**Cost**: ~$0.20-0.25 per workflow  
**Quality**: Best possible insights

## Testing Your Setup

### Run a Quick Test

```python
from graph_analytics_ai.ai.workflow import run_agentic_workflow

result = run_agentic_workflow(
    requirements_document="your_requirements.md",
    graph_name="your_graph",
    output_dir="./test_output"
)
```

### Check the Reports

Look in `test_output/` for generated reports. Quality reports should have:

- ✅ 3-5 distinct insights (not 1)
- ✅ Specific numbers and percentages
- ✅ Concrete business impacts
- ✅ Varied insight types

### Example: Good vs. Bad Insights

**Before (Bad)**:
```
Title: LLM Analysis
Description: Node P123 has the highest PageRank score. (truncated...)
Business Impact: Derived from AI analysis of results
Confidence: 85%
```

**After (Good)**:
```
Title: Top 5 Products Account for 82% of Network Influence
Description: Analysis of 500 products shows extreme concentration. The top 5 products (1% of total) have cumulative PageRank of 0.82, indicating they drive most purchase decisions. Product 'P123' leads with rank 0.28 (10x median of 0.028).
Business Impact: Focus marketing budget on these 5 products. Their performance disproportionately affects revenue. Monitor for single points of failure.
Confidence: 95%
```

## Running Tests

### Unit Tests
```bash
pytest tests/unit/ai/reporting/test_generator.py -v
```

### Integration Tests
```bash
pytest tests/integration/test_report_quality.py --run-integration -v
```

## Troubleshooting

### Reports Still Have Generic Insights

Check that LLM interpretation is enabled:
```python
import os
print(os.getenv("GAE_PLATFORM_USE_LLM_REPORTING", "true"))
```

### Too Many Low-Quality Insights Filtered

Lower the confidence threshold:
```bash
export GAE_PLATFORM_REPORTING_MIN_CONFIDENCE=0.4
```

### LLM Costs Too High

Switch to heuristic mode:
```bash
export GAE_PLATFORM_USE_LLM_REPORTING=false
```

## Advanced Usage

### Programmatic Configuration

```python
from graph_analytics_ai.ai.reporting.config import LLMReportingConfig, ReportConfig
from graph_analytics_ai.ai.reporting import ReportGenerator

# Create custom config
llm_config = LLMReportingConfig(
    use_llm_interpretation=True,
    use_reasoning_chain=True,
    min_confidence=0.7,
    max_insights_per_report=6
)

report_config = ReportConfig(llm_config=llm_config)

# Use in generator
generator = ReportGenerator(llm_provider=my_llm)
generator.config = llm_config
```

### Enable Reasoning Chain

For explainable AI with chain-of-thought:
```bash
export GAE_PLATFORM_REPORTING_USE_REASONING=true
```

This makes the LLM show its analytical process before generating insights.

## Best Practices

1. **Start with defaults** - They work well for most cases
2. **Monitor costs** - Check LLM usage in first week
3. **Adjust as needed** - Fine-tune confidence thresholds based on results
4. **Use reasoning mode** - For critical business decisions
5. **Test both modes** - Compare LLM vs heuristic for your use case

## Getting Help

- Documentation: `docs/agent-quality/AGENT_QUALITY_FINAL_REPORT.md`
- Environment Variables: `docs/ENVIRONMENT_VARIABLES.md`
- Implementation Details: `docs/agent-quality/AGENT_QUALITY_IMPLEMENTATION_SUMMARY.md`

## Summary

- ✅ Better reports automatically
- ✅ 3-5 specific insights per report
- ✅ Configurable quality vs. cost
- ✅ No code changes required
- ✅ Backwards compatible

Enjoy your improved reports!
