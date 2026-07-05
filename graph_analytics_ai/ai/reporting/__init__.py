"""
GAE Analysis Report Generation Module

Generates actionable intelligence reports from GAE analysis results.
Provides insights, recommendations, execution metrics, and multiple output formats.
Includes interactive HTML reports with Plotly charts.
"""

from .generator import ReportGenerator, generate_report
from .models import AnalysisReport, ReportSection, Insight, Recommendation, ReportFormat
from .config import (
    ReportConfig,
    WorkflowReportConfig,
    ReportSection as ConfigReportSection,
)
from .formatter import ExecutionReportFormatter
from .custom_verticals import (
    load_custom_vertical,
    load_platform_custom_vertical,
    register_custom_vertical,
    save_custom_vertical,
    get_industry_prompt_with_custom,
    list_all_verticals,
)
from .vertical_schema import validate_vertical_schema, get_example_vertical

# Optional chart generation (requires plotly)
try:
    from .chart_generator import ChartGenerator, is_plotly_available
    from .html_formatter import HTMLReportFormatter

    _charts_available = True
except ImportError:
    _charts_available = False
    ChartGenerator = None
    HTMLReportFormatter = None

    def is_plotly_available():
        return False


__all__ = [
    "ReportGenerator",
    "generate_report",
    "AnalysisReport",
    "ReportSection",
    "Insight",
    "Recommendation",
    "ReportFormat",
    "ReportConfig",
    "WorkflowReportConfig",
    "ConfigReportSection",
    "ExecutionReportFormatter",
    "ChartGenerator",
    "HTMLReportFormatter",
    "is_plotly_available",
    # Custom vertical support
    "load_custom_vertical",
    "load_platform_custom_vertical",
    "register_custom_vertical",
    "save_custom_vertical",
    "get_industry_prompt_with_custom",
    "list_all_verticals",
    "validate_vertical_schema",
    "get_example_vertical",
]
