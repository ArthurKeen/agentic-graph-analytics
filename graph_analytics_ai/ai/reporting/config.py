"""
Report configuration for customizing workflow outputs.

Allows users to control what sections and metrics are included in generated reports.
"""

import os
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
class LLMReportingConfig:
    """
    Configuration for LLM-based insight generation.
    
    Controls how LLM is used for report generation and quality standards.
    
    Example:
        >>> from graph_analytics_ai.ai.reporting.config import LLMReportingConfig
        >>>
        >>> # Enable LLM with strict quality standards
        >>> config = LLMReportingConfig(
        ...     use_llm_interpretation=True,
        ...     min_confidence=0.7,
        ...     use_reasoning_chain=True
        ... )
        >>>
        >>> # Cost-optimized configuration
        >>> config = LLMReportingConfig(
        ...     use_llm_interpretation=True,
        ...     max_insights_per_report=3,
        ...     llm_timeout_seconds=20
        ... )
    """
    
    use_llm_interpretation: bool = field(
        default_factory=lambda: os.getenv("GAE_PLATFORM_USE_LLM_REPORTING", "true").lower() == "true"
    )
    """Enable LLM-based insight generation (default: True, can set via GAE_PLATFORM_USE_LLM_REPORTING env var)."""
    
    min_confidence: float = field(
        default_factory=lambda: float(os.getenv("GAE_PLATFORM_REPORTING_MIN_CONFIDENCE", "0.3"))
    )
    """Minimum confidence threshold for insights (default: 0.3, can set via GAE_PLATFORM_REPORTING_MIN_CONFIDENCE)."""
    
    use_reasoning_chain: bool = field(
        default_factory=lambda: os.getenv("GAE_PLATFORM_REPORTING_USE_REASONING", "false").lower() == "true"
    )
    """Enable chain-of-thought reasoning for insight generation (default: False, can set via GAE_PLATFORM_REPORTING_USE_REASONING)."""
    
    max_insights_per_report: int = field(
        default_factory=lambda: int(os.getenv("GAE_PLATFORM_MAX_LLM_INSIGHTS_PER_REPORT", "5"))
    )
    """Maximum number of LLM insights per report (default: 5, can set via GAE_PLATFORM_MAX_LLM_INSIGHTS_PER_REPORT)."""
    
    llm_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("GAE_PLATFORM_LLM_REPORTING_TIMEOUT", "30"))
    )
    """Timeout for LLM calls in seconds (default: 30, can set via GAE_PLATFORM_LLM_REPORTING_TIMEOUT)."""
    
    fallback_to_heuristics: bool = True
    """Fallback to heuristic insights if LLM fails (always True for reliability)."""
    
    min_description_length: int = 100
    """Minimum description length for quality validation."""
    
    min_title_length: int = 15
    """Minimum title length for quality validation."""
    
    require_quantification: bool = True
    """Require insights to include numbers/metrics."""
    
    filter_generic_impacts: bool = True
    """Filter out insights with generic business impacts."""
    
    def __post_init__(self):
        """Post-initialization validation."""
        if self.min_confidence < 0.0 or self.min_confidence > 1.0:
            raise ValueError(f"min_confidence must be between 0.0 and 1.0, got {self.min_confidence}")
        
        if self.max_insights_per_report < 1:
            raise ValueError(f"max_insights_per_report must be >= 1, got {self.max_insights_per_report}")
        
        if self.llm_timeout_seconds < 1:
            raise ValueError(f"llm_timeout_seconds must be >= 1, got {self.llm_timeout_seconds}")


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
    
    llm_config: LLMReportingConfig = field(default_factory=LLMReportingConfig)
    """Configuration for LLM-based insight generation."""

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
