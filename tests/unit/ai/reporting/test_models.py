"""Tests for reporting models."""

from datetime import datetime
from graph_analytics_ai.ai.reporting.models import (
    ReportFormat,
    InsightType,
    Insight,
    AnalysisReport,
)


class TestReportFormat:
    """Tests for ReportFormat enum."""

    def test_formats_exist(self):
        """Test that all expected formats exist."""
        assert ReportFormat.MARKDOWN.value == "markdown"
        assert ReportFormat.JSON.value == "json"
        assert ReportFormat.HTML.value == "html"
        assert ReportFormat.TEXT.value == "text"


class TestInsightType:
    """Tests for InsightType enum."""

    def test_insight_types_exist(self):
        """Test that all expected insight types exist."""
        assert InsightType.PATTERN.value == "pattern"
        assert InsightType.ANOMALY.value == "anomaly"
        assert InsightType.TREND.value == "trend"


class TestReportModels:
    """Basic tests for report models."""

    def test_insight_import(self):
        """Test Insight model can be imported and used."""
        insight = Insight(
            title="Test",
            description="Test",
            insight_type=InsightType.PATTERN,
            confidence=0.9,
            supporting_data={},
        )
        assert insight.title == "Test"

    def test_report_import(self):
        """Test AnalysisReport model can be imported and used."""
        report = AnalysisReport(
            title="Test Report",
            summary="Summary",
            algorithm="pagerank",
            generated_at=datetime.now(),
            insights=[],
            recommendations=[],
        )
        assert report.title == "Test Report"
