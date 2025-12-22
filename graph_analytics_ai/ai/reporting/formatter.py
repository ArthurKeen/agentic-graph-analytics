"""
Execution report formatter.

Generates markdown reports from execution metrics with configurable sections.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path

from .config import ReportConfig, ReportSection
from ..execution.metrics import ExecutionSummary, TimingBreakdown, CostBreakdown


class ExecutionReportFormatter:
    """
    Formats execution metrics into readable reports.

    Supports customizable sections and multiple output formats.

    Example:
        >>> from graph_analytics_ai.ai.reporting.formatter import ExecutionReportFormatter
        >>> from graph_analytics_ai.ai.reporting.config import ReportConfig
        >>>
        >>> formatter = ExecutionReportFormatter(ReportConfig())
        >>> report_md = formatter.format_report(execution_summary)
        >>>
        >>> # Save to file
        >>> Path("execution_report.md").write_text(report_md)
    """

    def __init__(self, config: Optional[ReportConfig] = None):
        """
        Initialize formatter.

        Args:
            config: Report configuration (uses defaults if not provided)
        """
        self.config = config or ReportConfig()

    def format_report(self, summary: ExecutionSummary) -> str:
        """
        Format execution summary as markdown report.

        Args:
            summary: Execution summary to format

        Returns:
            Formatted markdown report
        """
        sections = []

        # Title
        sections.append(self._format_title(summary))

        # Executive Summary
        if self.config.should_include(ReportSection.EXECUTIVE_SUMMARY):
            sections.append(self._format_executive_summary(summary))

        # Timing Breakdown
        if (
            self.config.should_include(ReportSection.TIMING_BREAKDOWN)
            and summary.timing_breakdown
        ):
            sections.append(self._format_timing_breakdown(summary.timing_breakdown))

        # Cost Analysis
        if (
            self.config.should_include(ReportSection.COST_ANALYSIS)
            and self.config.include_costs
            and summary.cost_breakdown
        ):
            sections.append(self._format_cost_breakdown(summary.cost_breakdown))

        # Performance Metrics
        if self.config.should_include(ReportSection.PERFORMANCE_METRICS):
            sections.append(self._format_performance_metrics(summary))

        # Algorithm Details
        if self.config.should_include(ReportSection.ALGORITHM_DETAILS):
            sections.append(self._format_algorithm_details(summary))

        # Error Log
        if (
            self.config.should_include(ReportSection.ERROR_LOG)
            and summary.errors
            and self.config.include_error_details
        ):
            sections.append(self._format_error_log(summary))

        # Raw Metrics
        if (
            self.config.should_include(ReportSection.RAW_METRICS)
            and self.config.include_raw_metrics
        ):
            sections.append(self._format_raw_metrics(summary))

        return "\n\n".join(sections)

    def _format_title(self, summary: ExecutionSummary) -> str:
        """Format report title."""
        lines = ["# GAE Execution Report", ""]

        if self.config.show_timestamps:
            lines.extend(
                [
                    f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
                    f"**Workflow ID:** `{summary.workflow_id}`  ",
                ]
            )

            if summary.started_at:
                lines.append(
                    f"**Started:** {summary.started_at.strftime('%Y-%m-%d %H:%M:%S')}  "
                )
            if summary.completed_at:
                lines.append(
                    f"**Completed:** {summary.completed_at.strftime('%Y-%m-%d %H:%M:%S')}  "
                )

        return "\n".join(lines)

    def _format_executive_summary(self, summary: ExecutionSummary) -> str:
        """Format executive summary section."""
        lines = ["## Executive Summary", ""]

        # Overall status
        status_emoji = "✅" if summary.templates_failed == 0 else "⚠️"
        lines.extend(
            [
                f"**Status:** {status_emoji} {summary.templates_succeeded} of {summary.templates_executed} succeeded",
                f"**Success Rate:** {summary.success_rate:.1f}%",
                f"**Total Duration:** {summary.total_duration_seconds:.1f}s",
            ]
        )

        # Cost summary (if available)
        if summary.cost_breakdown and self.config.include_costs:
            lines.append(
                f"**Total Cost:** ${summary.cost_breakdown.total_cost_usd:.4f} USD"
            )

        # Resource info
        if summary.engine_size:
            lines.append(f"**Engine Size:** {summary.engine_size}")

        if summary.deployment_mode:
            lines.append(f"**Deployment:** {summary.deployment_mode}")

        # Quick stats
        lines.extend(
            [
                "",
                "### Quick Stats",
                "",
                f"- **Vertices Processed:** {summary.total_vertices_processed:,}",
                f"- **Edges Processed:** {summary.total_edges_processed:,}",
                f"- **Results Generated:** {summary.total_results_generated:,}",
                f"- **Algorithms Run:** {len(summary.algorithm_stats)}",
            ]
        )

        return "\n".join(lines)

    def _format_timing_breakdown(self, timing: TimingBreakdown) -> str:
        """Format timing breakdown section."""
        lines = [
            "## Timing Breakdown",
            "",
            "| Phase | Duration | Percentage |",
            "|-------|----------|------------|",
        ]

        decimals = self.config.decimal_places

        # Add rows
        lines.append(
            f"| Graph Loading | {timing.graph_load_seconds:.{decimals}f}s | "
            f"{timing.load_percentage:.1f}% |"
        )
        lines.append(
            f"| Algorithm Execution | {timing.algorithm_execution_seconds:.{decimals}f}s | "
            f"{timing.execution_percentage:.1f}% |"
        )
        lines.append(
            f"| Results Storage | {timing.results_store_seconds:.{decimals}f}s | "
            f"{timing.storage_percentage:.1f}% |"
        )
        lines.append(
            f"| **Total** | **{timing.total_seconds:.{decimals}f}s** | **100.0%** |"
        )

        # Add chart if showing percentages
        if self.config.show_percentages:
            lines.extend(
                [
                    "",
                    "### Time Distribution",
                    "",
                    "```",
                    f"Load:      {'█' * int(timing.load_percentage / 2)} {timing.load_percentage:.1f}%",
                    f"Execute:   {'█' * int(timing.execution_percentage / 2)} {timing.execution_percentage:.1f}%",
                    f"Store:     {'█' * int(timing.storage_percentage / 2)} {timing.storage_percentage:.1f}%",
                    "```",
                ]
            )

        return "\n".join(lines)

    def _format_cost_breakdown(self, cost: CostBreakdown) -> str:
        """Format cost breakdown section."""
        lines = [
            "## Cost Analysis",
            "",
            f"**Engine Size:** {cost.engine_size or 'N/A'}  ",
            f"**Runtime:** {cost.runtime_minutes:.2f} minutes  ",
            "",
            "| Component | Cost (USD) |",
            "|-----------|------------|",
        ]

        decimals = self.config.decimal_places + 2  # More precision for costs

        lines.append(
            f"| Engine Deployment | ${cost.engine_deployment_cost_usd:.{decimals}f} |"
        )
        lines.append(f"| Runtime | ${cost.runtime_cost_usd:.{decimals}f} |")

        if cost.storage_cost_usd > 0:
            lines.append(f"| Storage | ${cost.storage_cost_usd:.{decimals}f} |")

        lines.append(f"| **Total** | **${cost.total_cost_usd:.{decimals}f}** |")

        # Add cost per minute
        cost_per_minute = (
            cost.runtime_cost_usd / cost.runtime_minutes
            if cost.runtime_minutes > 0
            else 0
        )
        lines.extend(
            ["", f"**Cost per Minute:** ${cost_per_minute:.{decimals}f} USD/min"]
        )

        return "\n".join(lines)

    def _format_performance_metrics(self, summary: ExecutionSummary) -> str:
        """Format performance metrics section."""
        lines = [
            "## Performance Metrics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
        ]

        # Processing metrics
        lines.extend(
            [
                f"| Total Vertices | {summary.total_vertices_processed:,} |",
                f"| Total Edges | {summary.total_edges_processed:,} |",
                f"| Total Results | {summary.total_results_generated:,} |",
            ]
        )

        # Throughput calculations
        if summary.total_execution_time_seconds > 0:
            vertices_per_sec = (
                summary.total_vertices_processed / summary.total_execution_time_seconds
            )
            edges_per_sec = (
                summary.total_edges_processed / summary.total_execution_time_seconds
            )

            lines.extend(
                [
                    f"| Vertices/Second | {vertices_per_sec:,.0f} |",
                    f"| Edges/Second | {edges_per_sec:,.0f} |",
                ]
            )

        # Execution stats
        lines.extend(
            [
                f"| Templates Executed | {summary.templates_executed} |",
                f"| Successful | {summary.templates_succeeded} |",
                f"| Failed | {summary.templates_failed} |",
                f"| Success Rate | {summary.success_rate:.1f}% |",
            ]
        )

        return "\n".join(lines)

    def _format_algorithm_details(self, summary: ExecutionSummary) -> str:
        """Format algorithm details section."""
        lines = ["## Algorithm Execution Details", ""]

        if not summary.algorithm_stats:
            lines.append("*No algorithm executions recorded.*")
            return "\n".join(lines)

        # Table header
        lines.extend(
            [
                "| Algorithm | Status | Duration | Vertices | Edges | Results | Retries |",
                "|-----------|--------|----------|----------|-------|---------|---------|",
            ]
        )

        # Sort by execution time (descending)
        sorted_stats = sorted(
            summary.algorithm_stats.values(),
            key=lambda x: x.execution_time_seconds,
            reverse=True,
        )

        # Limit to max_algorithm_details
        for stats in sorted_stats[: self.config.max_algorithm_details]:
            status_emoji = "✅" if stats.status == "completed" else "❌"
            lines.append(
                f"| {stats.algorithm} | {status_emoji} {stats.status} | "
                f"{stats.execution_time_seconds:.2f}s | "
                f"{stats.vertex_count:,} | "
                f"{stats.edge_count:,} | "
                f"{stats.results_count:,} | "
                f"{stats.retry_count} |"
            )

        if len(summary.algorithm_stats) > self.config.max_algorithm_details:
            remaining = len(summary.algorithm_stats) - self.config.max_algorithm_details
            lines.append(f"\n*...and {remaining} more algorithm executions.*")

        return "\n".join(lines)

    def _format_error_log(self, summary: ExecutionSummary) -> str:
        """Format error log section."""
        lines = ["## Error Log", ""]

        if not summary.errors:
            lines.append("*No errors encountered.* ✅")
            return "\n".join(lines)

        lines.append(f"**Total Errors:** {len(summary.errors)}")
        lines.append("")

        for i, error in enumerate(summary.errors, 1):
            lines.append(f"{i}. {error}")

        return "\n".join(lines)

    def _format_raw_metrics(self, summary: ExecutionSummary) -> str:
        """Format raw metrics section."""
        import json

        lines = ["## Raw Metrics (JSON)", "", "```json"]

        metrics_dict = summary.to_dict()
        lines.append(json.dumps(metrics_dict, indent=2))
        lines.append("```")

        return "\n".join(lines)

    def save_report(self, summary: ExecutionSummary, output_path: Path) -> Path:
        """
        Generate and save report to file.

        Args:
            summary: Execution summary to format
            output_path: Path to save report

        Returns:
            Path to saved report
        """
        report_content = self.format_report(summary)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_content)
        return output_path
