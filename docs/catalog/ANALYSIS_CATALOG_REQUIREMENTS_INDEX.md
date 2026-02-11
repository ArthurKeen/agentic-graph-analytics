# Analysis Catalog - Complete Requirements Index

**Version:** 2.0 
**Date:** 2026-01-06 
**Status:** Comprehensive Requirements List

---

## Requirements Summary by Priority

### P0: Must Have (MVP - Phase 1-2)

| ID | Requirement | Description | Benefit |
|----|-------------|-------------|---------|
| **FR-1** | **Execution Tracking** | Track all analysis executions with complete metadata | Core functionality |
| **FR-2** | **Epoch Management** | Create and manage analysis epochs | Time-series analysis foundation |
| **FR-3** | **Query and Retrieval** | Query executions by various criteria | Essential for analysis |
| **FR-4** | **Catalog Management** | CRUD operations, delete, reset | Operational necessity |
| **FR-5** | **Storage Backend** | ArangoDB, SQLite, PostgreSQL support | Data persistence |
| **FR-6** | **Workflow Integration** | Support all 3 workflow modes | Universal compatibility |
| **FR-7** | **Lineage Tracking** | Track requirements → templates → executions | Full traceability |

### P1: Should Have (MVP - Phase 2-3)

| ID | Requirement | Description | Benefit |
|----|-------------|-------------|---------|
| **FR-8** | **Time-Series Analysis** | Query metrics across epochs | Core value proposition |
| **FR-9** | **Performance Benchmarking** | Track execution time, cost, resources | Optimization & cost control |
| **FR-10** | **Execution Comparison** | Compare executions & epochs in detail | Debug changes, root cause |
| **FR-11** | **Result Sampling** | Store top N + stats in catalog | Fast queries, 10-100x speedup |
| **FR-13** | **Alerting** | Trigger alerts on failures, anomalies, costs | Proactive monitoring |

 = **Critical for production operations**

### P2: Nice to Have (v2 - Phase 4-5)

| ID | Requirement | Description | Benefit |
|----|-------------|-------------|---------|
| **FR-12** | **Audit Trail** | Track who ran what, when, why | Compliance & governance |
| **FR-14** | **Schedule Tracking** | Track scheduled vs ad-hoc analyses | SLA monitoring |
| **FR-15** | **Dependencies** | Track analysis dependencies | Complex workflow mgmt |
| **FR-16** | **Template Versioning** | Version control for templates | Track experimentation |
| **FR-17** | **Golden Epochs** | Mark baseline epochs for regression testing | Quality gates |
| **FR-18** | **Data Quality** | Track data quality metrics | Result reliability |

### P3: Future (Post v2)

| ID | Requirement | Description | Benefit |
|----|-------------|-------------|---------|
| **FR-19** | **Collaboration** | Comments, annotations, sharing | Team features |
| **FR-20** | **Integration Hooks** | Webhooks, event streams | External system integration |

---

## Detailed Requirements

### FR-1: Execution Tracking (P0)

**Track all analysis executions with:**
- execution_id, epoch_id, timestamp
- algorithm, version, parameters
- template_id, requirements_id, use_case_id (lineage)
- graph_config (collections, counts)
- results_location, result_count
- execution_time, status, errors
- workflow_mode, metadata

**Automatic tracking** for all workflow modes.

---

### FR-2: Epoch Management (P0)

**Epoch structure:**
- epoch_id, name, description, timestamp
- status (active, completed, archived)
- tags, metadata, parent_epoch_id
- analysis_count, execution_ids

**Operations:**
- create_epoch, get_epoch, list_epochs
- delete_epoch (with cascade option)
- get_epoch_executions

---

### FR-3: Query and Retrieval (P0)

**Query by:**
- execution_id, epoch_id, algorithm
- date range, graph name, status
- requirements_id, use_case_id, template_id
- Combined filters with AND/OR logic

**Pagination** and **sorting** support.

---

### FR-4: Catalog Management (P0)

**Operations:**
- Delete single execution
- Delete epoch (cascade or orphan)
- Delete by date range or filter
- Bulk delete with confirmation
- Reset catalog (testing)
- Export/import (backup)

---

### FR-5: Storage Backend (P0)

**Supported backends:**
1. **ArangoDB** (default) - Same DB as graph
2. **SQLite** - Lightweight for testing
3. **PostgreSQL** - Large-scale deployments

**Requirements:**
- Efficient indexing
- JSON/nested field support
- Transaction support
- Backup/restore

---

### FR-6: Workflow Integration (P0)

**Support all 3 modes:**
1. **Traditional Orchestrator** - Step-by-step control
2. **Agentic Workflow** - Autonomous AI agents
3. **Parallel Agentic** - 40-60% faster

**Features:**
- Automatic tracking (transparent)
- Thread-safe for parallel
- Track workflow_mode in metadata

---

### FR-7: Lineage Tracking (P0)

**Track complete lineage:**
```
Requirements Document
 ↓ RequirementsAgent
Extracted Requirements
 ↓ UseCaseAgent 
Use Cases
 ↓ TemplateAgent
Templates
 ↓ ExecutionAgent
Executions
 ↓ ReportingAgent
Reports
```

**New collections:**
- `_analysis_requirements`
- `_analysis_use_cases`
- `_analysis_templates`
- `_analysis_executions` (enhanced)

**Lineage queries:**
- get_execution_lineage(execution_id)
- get_requirements_executions(requirements_id)
- trace_requirement(requirements_id, "REQ-001")

---

### FR-8: Time-Series Analysis (P1)

**Capabilities:**
- Extract metrics from result collections
- Query metric across epochs
- Time-series data (daily, weekly, monthly)
- Cross-epoch comparison as DataFrame
- Requirements history over time

**Example:**
```python
ts_data = catalog.get_time_series(
 metric="wcc.component_count",
 start_date="2026-01-01",
 end_date="2026-06-30",
 frequency="daily"
)
```

---

### FR-9: Performance Benchmarking (P1) 

**Track for each execution:**
```json
{
 "performance_metrics": {
 "execution_time_seconds": 45.3,
 "memory_usage_mb": 512,
 "memory_peak_mb": 768,
 "cpu_time_seconds": 120.5,
 "io_operations": 15000,
 "network_bytes": 1048576,
 "cost_usd": 0.023
 },
 "resource_config": {
 "engine_size": "e16",
 "cluster_nodes": 3,
 "parallel_workers": 8
 }
}
```

**Queries:**
- get_performance_trend(algorithm, date_range)
- detect_performance_regressions(threshold=0.2)
- compare_performance(group_by="engine_size")
- get_cost_report(date_range, group_by)

**Use Cases:**
- Identify performance regressions
- Optimize resource allocation
- Track and control costs
- Capacity planning
- Justify infrastructure investments

**Why Critical:**
- Essential for production operations
- Enables cost optimization
- Performance troubleshooting

---

### FR-10: Execution Comparison (P1) 

**Compare two executions:**
```python
diff = catalog.compare_executions("exec1", "exec2")
```

**Returns:**
- Parameter changes
- Result changes (top N rank changes)
- Metric changes (mean, std, percentiles)
- Performance changes (time, cost)
- Configuration changes (engine size, etc.)

**Compare two epochs:**
```python
epoch_diff = catalog.compare_epochs_detailed("2026-01", "2026-02")
```

**Returns:**
- New/removed/modified analyses
- Metric changes across all algorithms
- Performance summary
- Cost comparison

**Export:** HTML report with visualizations

**Use Cases:**
- Debug "why did results change?"
- Understand impact of parameter tuning
- Validate A/B tests
- Root cause analysis

**Why Critical:**
- Core to "analyze changes" goal
- Essential for debugging
- Answers the "why" questions

---

### FR-11: Result Sampling (P1) 

**Store in catalog:**
```json
{
 "result_sample": {
 "top_100": [
 {"_key": "customer_42", "score": 0.0456, "rank": 1},
 ...
 ],
 "summary_stats": {
 "mean": 0.0001,
 "median": 0.00008,
 "std_dev": 0.0002,
 "min": 0.00001,
 "max": 0.0456,
 "percentile_95": 0.0005,
 ...
 },
 "distribution_histogram": {
 "bins": [...],
 "counts": [...]
 }
 }
}
```

**Fast queries:**
```python
# Get top N instantly (no full scan)
top = catalog.get_sampled_results(execution_id, top_n=10)

# Compare across epochs instantly
comparison = catalog.compare_sampled_results(epoch_ids, top_n=20)

# Summary stats timeline
stats = catalog.get_stats_timeline(algorithm, stat="mean")
```

**Benefits:**
- **10-100x faster** time-series queries
- Works even if result collections deleted
- Enable quick "top movers" analysis
- Reduce load on result collections

**Trade-offs:**
- +1-2KB storage per execution
- Sample may not represent full distribution (use stats)

**Configuration:**
- Configurable sample size (default: 100)
- Configurable statistics
- Option to disable per algorithm

**Why Critical:**
- Makes time-series analysis practical
- Essential for responsive dashboards
- Enables real-time comparisons

---

### FR-12: Audit Trail (P2)

**Track per execution:**
```json
{
 "audit_info": {
 "initiated_by": "data_scientist@company.com",
 "initiated_from": "jupyter_notebook",
 "purpose": "Monthly KPI analysis",
 "cost_center": "marketing_analytics",
 "project_id": "Q1_analysis",
 "approved_by": "manager@company.com"
 }
}
```

**Queries:**
- get_user_activity(user, date_range)
- get_cost_by_cost_center(date_range)
- export_audit_log(format="csv")

**Use Cases:**
- Compliance & governance
- Usage tracking & chargeback
- Security audits
- Pattern analysis

---

### FR-13: Alerting and Monitoring (P1) 

**Alert types:**

1. **Execution Failures**
```python
catalog.create_alert(
 name="high_failure_rate",
 condition="failure_rate > 0.1 over last 24h",
 actions=[
 {"type": "email", "recipients": ["ops@company.com"]},
 {"type": "slack", "channel": "#data-ops"}
 ]
)
```

2. **Metric Anomalies**
```python
catalog.create_alert(
 name="pagerank_anomaly",
 condition="avg_score > mean + (2 * std_dev) from 30d baseline",
 actions=[{"type": "create_ticket", "priority": "high"}]
)
```

3. **Cost Overruns**
```python
catalog.create_alert(
 name="daily_cost_limit",
 condition="daily_cost > $100",
 actions=[{"type": "slack"}, {"type": "webhook"}]
)
```

4. **Performance Degradation**
```python
catalog.create_alert(
 name="slow_execution",
 condition="execution_time > 2 * avg over last 30d",
 actions=[{"type": "email"}]
)
```

5. **Missed Schedules**
```python
catalog.create_alert(
 name="schedule_miss",
 condition="scheduled_job_not_run within 1h",
 actions=[{"type": "pagerduty"}]
)
```

**Alert channels:**
- Email
- Slack
- PagerDuty
- Webhook (HTTP)
- Ticket systems (Jira, ServiceNow)

**Management:**
- list_alerts, update_alert, test_alert
- get_alert_history
- Enable/disable alerts

**Use Cases:**
- Catch failures early
- Detect anomalies automatically
- Control costs proactively
- Monitor SLAs
- Performance regression detection

**Why Critical:**
- Operational necessity
- Proactive problem detection
- Prevent surprises
- Essential for production

---

### FR-14: Scheduled Analysis Tracking (P2)

**Track scheduling info:**
```json
{
 "schedule_info": {
 "type": "scheduled",
 "schedule_id": "daily_pagerank",
 "schedule_cron": "0 2 * * *",
 "scheduled_time": "2026-01-01T02:00:00Z",
 "actual_start_time": "2026-01-01T02:00:15Z",
 "delay_seconds": 15
 }
}
```

**Queries:**
- get_schedule_reliability(schedule_id)
- get_scheduled_executions(schedule_id)
- get_schedule_delays_histogram()

**Use Cases:**
- SLA monitoring
- Distinguish routine vs exploratory
- Track scheduling reliability
- Identify usage patterns

---

### FR-15: Analysis Dependencies (P2)

**Dependency tracking:**
```python
# Add dependency
catalog.add_dependency(
 execution_id="exec2",
 depends_on="exec1",
 dependency_type="results"
)

# Validate before execution
if not catalog.validate_dependencies("exec2"):
 raise Exception("Dependencies not satisfied")

# Get dependency tree
tree = catalog.get_dependency_tree("exec5")

# Reverse lookup
dependents = catalog.get_dependents("exec1")
```

**Dependency types:**
- results: Depends on results from previous execution
- parameters: Uses parameters from previous execution
- config: Uses configuration from previous execution
- data: Depends on same data version

**Use Cases:**
- Ensure correct execution order
- Impact analysis (what breaks if this fails?)
- Troubleshoot cascading failures
- Reproducibility guarantees
- DAG-based scheduling

---

### FR-16: Template Version Control (P2)

**Versioning:**
```python
# Update creates new version
v2 = catalog.update_template(
 template_id="template_001",
 changes={"parameters": {"damping_factor": 0.90}},
 change_reason="Improve convergence",
 changed_by="analyst@company.com"
)

# Get version history
history = catalog.get_template_history("template_001")

# Compare versions
diff = catalog.diff_templates("template_001", from_version=1, to_version=2)

# Rollback
catalog.rollback_template("template_001", to_version=1)
```

**Use Cases:**
- Track parameter tuning experiments
- Understand what worked historically
- Rollback problematic changes
- Document learning
- Reproduce historical analyses

---

### FR-17: Golden/Reference Epochs (P2)

**Golden epoch management:**
```python
# Mark as golden baseline
catalog.mark_epoch_golden(
 epoch_id="2026-01-baseline",
 reason="Pre-migration baseline"
)

# Compare to golden
comparison = catalog.compare_to_golden(
 current_epoch_id="2026-06",
 golden_epoch_id="2026-01-baseline"
)

# Detect regressions
regressions = catalog.detect_regressions(
 current_epoch_id="2026-06",
 golden_epoch_id="2026-01-baseline",
 threshold=0.1 # 10% regression = alert
)
```

**Use Cases:**
- Regression testing
- A/B test baselines
- Pre/post migration comparisons
- Quality gates
- Validate system changes

---

### FR-18: Data Quality Metrics (P2)

**Quality tracking:**
```json
{
 "data_quality": {
 "graph_freshness_hours": 2.5,
 "data_completeness_score": 0.98,
 "missing_data_percentage": 0.02,
 "orphaned_vertices": 10,
 "self_loops": 5,
 "validation_passed": true,
 "quality_score": 0.95,
 "warnings": [
 "10 orphaned vertices in customers",
 "Graph freshness exceeds 4 hours"
 ]
 }
}
```

**Queries:**
- Filter by quality score
- get_quality_trend(algorithm, date_range)
- get_low_quality_executions(threshold=0.8)

**Use Cases:**
- Track result reliability
- Filter analyses by quality
- Identify data issues
- Compliance reporting
- Set quality gates

---

### FR-19: Collaboration Features (P3)

**Comments and annotations:**
```python
# Add comment
catalog.add_comment(
 execution_id="exec1",
 comment="Unusual spike - investigate pipeline",
 author="analyst@company.com"
)

# Annotate epoch
catalog.annotate(
 epoch_id="2026-01",
 annotation="Marketing campaign launched",
 annotation_type="external_event"
)
```

**Sharing:**
```python
catalog.share(
 execution_id="exec1",
 with_users=["team@company.com"],
 permissions="read"
)

catalog.bookmark(execution_id="exec1")
```

---

### FR-20: Integration Hooks (P3)

**Webhooks:**
```python
catalog.register_webhook(
 event="execution_completed",
 url="https://api.company.com/webhooks",
 filters={"algorithm": "pagerank"}
)
```

**Event stream:**
```python
for event in catalog.stream_events():
 send_to_data_warehouse(event)
```

**Events:**
- execution_started, execution_completed, execution_failed
- epoch_created, epoch_completed
- alert_triggered
- template_updated

---

## Implementation Roadmap

### Phase 1: Core Infrastructure (4 weeks)
- FR-1: Execution Tracking
- FR-2: Epoch Management
- FR-5: Storage Backend (ArangoDB)
- FR-6: Workflow Integration (basic)

### Phase 2: Essential Queries & Operations (3 weeks)
- FR-3: Query and Retrieval
- FR-4: Catalog Management
- FR-6: Workflow Integration (complete)
- FR-7: Lineage Tracking

### Phase 3: Time-Series & Performance (4 weeks)
- FR-8: Time-Series Analysis
- **FR-9: Performance Benchmarking** 
- **FR-10: Execution Comparison** 
- **FR-11: Result Sampling** 

### Phase 4: Operations & Monitoring (3 weeks)
- **FR-13: Alerting** 
- FR-14: Schedule Tracking
- FR-12: Audit Trail

### Phase 5: Advanced Features (4 weeks)
- FR-15: Dependencies
- FR-16: Template Versioning
- FR-17: Golden Epochs
- FR-18: Data Quality

### Future Releases
- FR-19: Collaboration
- FR-20: Integration Hooks

---

## Estimated Timeline

**MVP (Phases 1-3):** 11 weeks
- Includes all P0 requirements
- Includes critical P1 requirements (FR-9, FR-10, FR-11)

**v2 (Phases 4-5):** +7 weeks (total 18 weeks)
- Includes alerting (FR-13)
- Includes nice-to-have P2 requirements

**Post v2:** Future releases
- P3 requirements as needed

---

## Success Metrics

### Adoption
- 90%+ of analyses tracked in catalog
- 20+ epochs created per month
- 100+ catalog queries per day

### Performance
- Query latency P95 < 1 second
- Sampling reduces query time by 10-100x
- Storage overhead < 5% of result sizes

### Operations
- Alert response time < 5 minutes
- 99% uptime for catalog
- Zero data loss incidents

---

## Recommended MVP Scope

Based on analysis, **strongly recommend including FR-9, FR-10, FR-11, FR-13** in MVP:

**MVP = Phases 1-4** (14 weeks total)
- All P0 requirements (core functionality)
- Critical P1 requirements (performance, comparison, sampling, alerting)
- Production-ready with operational capabilities

**Alternative Minimal MVP = Phases 1-2** (7 weeks)
- Core functionality only
- No performance tracking, comparison, or alerting
- **Not recommended** - limits production usefulness

---

## Questions for Decision

1. **Cost Tracking**: Include cloud provider cost integration in FR-9?
2. **Alert Channels**: Which to support initially (Email, Slack, PagerDuty)?
3. **Sample Size**: Default top 100 or configurable?
4. **Audit Requirements**: Compliance needs for FR-12?
5. **MVP Scope**: Include FR-9, FR-10, FR-11, FR-13 in MVP? (Recommended: YES)

---

**Status:** Ready for review and implementation planning 
**Next Steps:** 
1. Confirm MVP scope
2. Answer decision questions
3. Create implementation tickets
4. Begin Phase 1 development

