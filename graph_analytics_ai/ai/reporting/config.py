"""
Report configuration for customizing workflow outputs.

Allows users to control what sections and metrics are included in generated reports.
"""

from dataclasses import dataclass, field
from typing import List
from enum import Enum


class ReportFormat(Enum):
    """Output format for reports."""

    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    TEXT = "text"


class ReportSection(Enum):
    """Available report sections."""

    EXECUTIVE_SUMMARY = "executive_summary"
    TIMING_BREAKDOWN = "timing_breakdown"
    COST_ANALYSIS = "cost_analysis"
    PERFORMANCE_METRICS = "performance_metrics"
    ALGORITHM_DETAILS = "algorithm_details"
    ERROR_LOG = "error_log"
    RECOMMENDATIONS = "recommendations"
    RAW_METRICS = "raw_metrics"


@dataclass
class ReportConfig:
    """
    Configuration for report generation.

    Allows customization of what content to include in reports.

    Example:
        >>> from graph_analytics_ai.ai.reporting.config import ReportConfig, ReportSection
        >>>
        >>> # Executive summary only
        >>> config = ReportConfig(
        ...     include_sections=[ReportSection.EXECUTIVE_SUMMARY],
        ...     include_costs=False
        ... )
        >>>
        >>> # Full detailed report
        >>> config = ReportConfig(
        ...     include_all_sections=True,
        ...     include_detailed_timing=True,
        ...     include_error_details=True
        ... )
    """

    include_sections: List[ReportSection] = field(
        default_factory=lambda: [
            ReportSection.EXECUTIVE_SUMMARY,
            ReportSection.TIMING_BREAKDOWN,
            ReportSection.COST_ANALYSIS,
            ReportSection.PERFORMANCE_METRICS,
            ReportSection.ALGORITHM_DETAILS,
        ]
    )
    """Sections to include in report."""

    include_all_sections: bool = False
    """Include all available sections."""

    include_costs: bool = True
    """Include cost analysis (AMP only)."""

    include_detailed_timing: bool = True
    """Include detailed timing breakdown."""

    include_error_details: bool = True
    """Include detailed error information."""

    include_raw_metrics: bool = False
    """Include raw JSON metrics."""

    format: ReportFormat = ReportFormat.MARKDOWN
    """Output format for report."""

    max_algorithm_details: int = 10
    """Maximum number of algorithms to show detailed stats for."""

    show_timestamps: bool = True
    """Include timestamps in report."""

    show_percentages: bool = True
    """Show percentage breakdowns."""

    decimal_places: int = 2
    """Number of decimal places for metrics."""

    def __post_init__(self):
        """Post-initialization validation."""
        if self.include_all_sections:
            self.include_sections = list(ReportSection)

    def should_include(self, section: ReportSection) -> bool:
        """Check if a section should be included."""
        return section in self.include_sections

    def get_active_sections(self) -> List[ReportSection]:
        """Get list of active sections."""
        return self.include_sections.copy()


@dataclass
class WorkflowReportConfig:
    """
    Configuration for all workflow reports.

    Allows different configurations for different report types.
    """

    execution_report: ReportConfig = field(default_factory=ReportConfig)
    """Configuration for execution reports."""

    schema_report: ReportConfig = field(
        default_factory=lambda: ReportConfig(
            include_sections=[
                ReportSection.EXECUTIVE_SUMMARY,
                ReportSection.PERFORMANCE_METRICS,
            ],
            include_costs=False,
        )
    )
    """Configuration for schema analysis reports."""

    use_case_report: ReportConfig = field(
        default_factory=lambda: ReportConfig(
            include_sections=[
                ReportSection.EXECUTIVE_SUMMARY,
                ReportSection.ALGORITHM_DETAILS,
            ],
            include_costs=False,
        )
    )
    """Configuration for use case reports."""

    enable_execution_reporting: bool = True
    """Whether to generate execution reports at all."""

    save_intermediate_reports: bool = True
    """Save reports after each major step."""

    report_directory: str = "reports"
    """Subdirectory for reports within output_dir."""
