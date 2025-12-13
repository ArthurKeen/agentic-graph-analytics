"""
GAE Analysis Report Generation Module

Generates actionable intelligence reports from GAE analysis results.
Provides insights, recommendations, and multiple output formats.
"""

from .generator import ReportGenerator, generate_report
from .models import (
    AnalysisReport,
    ReportSection,
    Insight,
    Recommendation,
    ReportFormat
)

__all__ = [
    "ReportGenerator",
    "generate_report",
    "AnalysisReport",
    "ReportSection",
    "Insight",
    "Recommendation",
    "ReportFormat",
]

