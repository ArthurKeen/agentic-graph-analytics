"""
Tests for Phase 3: Executive summary, risk assessment, and action items.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from graph_analytics_ai.ai.reporting.generator import ReportGenerator
from graph_analytics_ai.ai.reporting.models import (
    AnalysisReport,
    Insight,
    InsightType,
    Recommendation,
    RecommendationType,
)
from graph_analytics_ai.ai.execution.models import (
    AnalysisJob,
    ExecutionResult,
    ExecutionStatus,
)


class TestExecutiveSummary:
    """Test executive summary generation."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = ReportGenerator(
            llm_provider=Mock(), use_llm_interpretation=False
        )

    def test_generate_summary_basic(self):
        """Test basic summary generation."""
        report = AnalysisReport(
            title="Test Report",
            summary="",
            generated_at=datetime.now(),
            algorithm="pagerank",
            dataset_info={"result_count": 1000},
            insights=[
                Insight(
                    title="Top Node Found",
                    description="Analysis shows node X is most important",
                    confidence=0.85,
                    insight_type=InsightType.KEY_FINDING,
                    business_impact="Focus on this node",
                )
            ],
            recommendations=[],
        )

        summary = self.generator._generate_summary(report)

        assert "1,000 results" in summary
        assert "pagerank" in summary
        assert "1 key insights" in summary or "1 key insight" in summary

    def test_generate_summary_with_top_insight(self):
        """Test summary includes top confidence insight."""
        report = AnalysisReport(
            title="Test Report",
            summary="",
            generated_at=datetime.now(),
            algorithm="wcc",
            dataset_info={"result_count": 500},
            insights=[
                Insight(
                    title="Low confidence finding",
                    description="Something minor",
                    confidence=0.4,
                    insight_type=InsightType.KEY_FINDING,
                    business_impact="Not critical",
                ),
                Insight(
                    title="Critical Botnet Detected",
                    description="High confidence fraud detection",
                    confidence=0.92,
                    insight_type=InsightType.ANOMALY,
                    business_impact="IMMEDIATE action required",
                ),
            ],
            recommendations=[],
        )

        summary = self.generator._generate_summary(report)

        assert "Critical Botnet Detected" in summary
        assert "highest confidence" in summary.lower()

    def test_generate_summary_with_high_priority_actions(self):
        """Test summary mentions high priority actions."""
        report = AnalysisReport(
            title="Test Report",
            summary="",
            generated_at=datetime.now(),
            algorithm="pagerank",
            dataset_info={"result_count": 100},
            insights=[],
            recommendations=[
                Recommendation(
                    title="Fix issue",
                    description="Do this now",
                    recommendation_type=RecommendationType.ACTION,
                    priority="critical",
                ),
                Recommendation(
                    title="Another fix",
                    description="Also urgent",
                    recommendation_type=RecommendationType.ACTION,
                    priority="high",
                ),
                Recommendation(
                    title="Minor improvement",
                    description="Later",
                    recommendation_type=RecommendationType.OPTIMIZATION,
                    priority="low",
                ),
            ],
        )

        summary = self.generator._generate_summary(report)

        assert "2 immediate action" in summary


class TestRiskAssessment:
    """Test risk level assessment."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = ReportGenerator(
            llm_provider=Mock(), use_llm_interpretation=False
        )

    def test_assess_risk_critical(self):
        """Test CRITICAL risk assessment for fraud/botnet."""
        insights = [
            Insight(
                title="Botnet Detected at Node X",
                description="Clear fraud pattern with botnet signature",
                confidence=0.88,
                insight_type=InsightType.ANOMALY,
                business_impact="Block traffic immediately",
            )
        ]

        risk = self.generator._assess_risk_level(insights)

        assert risk == "CRITICAL"

    def test_assess_risk_high(self):
        """Test HIGH risk for multiple anomalies."""
        insights = [
            Insight(
                title="Suspicious Pattern in Cluster A",
                description="Anomalous behavior detected with high confidence",
                confidence=0.82,
                insight_type=InsightType.ANOMALY,
                business_impact="Risk of data quality issues",
            ),
            Insight(
                title="Over-aggregation Risk",
                description="Multiple households incorrectly merged",
                confidence=0.75,
                insight_type=InsightType.KEY_FINDING,
                business_impact="False positives in targeting",
            ),
        ]

        risk = self.generator._assess_risk_level(insights)

        assert risk in ["HIGH", "CRITICAL"]

    def test_assess_risk_medium(self):
        """Test MEDIUM risk for single anomaly."""
        insights = [
            Insight(
                title="Data Quality Issue Detected",
                description="Some data inconsistencies found but not critical",
                confidence=0.65,
                insight_type=InsightType.ANOMALY,
                business_impact="Monitor situation and validate data sources",
            )
        ]

        risk = self.generator._assess_risk_level(insights)

        # Should be MEDIUM or LOW (not CRITICAL) since it's a minor issue
        assert risk in ["MEDIUM", "LOW"]

    def test_assess_risk_low(self):
        """Test LOW risk for normal findings."""
        insights = [
            Insight(
                title="Network is Well Structured",
                description="Standard clustering patterns observed",
                confidence=0.90,
                insight_type=InsightType.PATTERN,
                business_impact="Continue current approach",
            )
        ]

        risk = self.generator._assess_risk_level(insights)

        assert risk == "LOW"

    def test_assess_risk_no_insights(self):
        """Test risk assessment with no insights."""
        risk = self.generator._assess_risk_level([])

        assert risk == "LOW"


class TestActionItemExtraction:
    """Test action item extraction."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = ReportGenerator(
            llm_provider=Mock(), use_llm_interpretation=False
        )

    def test_extract_action_items_from_insights(self):
        """Test extracting action items from insight business impacts."""
        report = AnalysisReport(
            title="Test Report",
            summary="",
            generated_at=datetime.now(),
            algorithm="wcc",
            dataset_info={"result_count": 100},
            insights=[
                Insight(
                    title="Fraud Detected",
                    description="Botnet pattern found",
                    confidence=0.90,
                    insight_type=InsightType.ANOMALY,
                    business_impact="IMMEDIATE: Block traffic from component X. RECOMMENDATION: Audit data sources.",
                )
            ],
            recommendations=[],
        )

        actions = self.generator._extract_action_items(report)

        assert len(actions) >= 1
        assert any("Block traffic" in action["action"] for action in actions)
        assert any(action["priority"] == "IMMEDIATE" for action in actions)

    def test_extract_action_items_from_recommendations(self):
        """Test extracting action items from recommendations."""
        report = AnalysisReport(
            title="Test Report",
            summary="",
            generated_at=datetime.now(),
            algorithm="pagerank",
            dataset_info={"result_count": 100},
            insights=[],
            recommendations=[
                Recommendation(
                    title="Fix Configuration",
                    description="Update clustering parameters to reduce false positives",
                    recommendation_type=RecommendationType.OPTIMIZATION,
                    priority="high",
                ),
                Recommendation(
                    title="Monitor System",
                    description="Set up alerts for anomalous patterns",
                    recommendation_type=RecommendationType.MONITORING,
                    priority="medium",
                ),
            ],
        )

        actions = self.generator._extract_action_items(report)

        assert len(actions) >= 2
        assert any("clustering parameters" in action["action"] for action in actions)
        assert actions[0]["priority"] in ["HIGH", "CRITICAL", "IMMEDIATE"]

    def test_action_items_sorted_by_priority(self):
        """Test that action items are sorted by priority."""
        report = AnalysisReport(
            title="Test Report",
            summary="",
            generated_at=datetime.now(),
            algorithm="wcc",
            dataset_info={"result_count": 100},
            insights=[
                Insight(
                    title="Minor Issue",
                    description="Low priority",
                    confidence=0.60,
                    insight_type=InsightType.KEY_FINDING,
                    business_impact="RECOMMENDATION: Consider optimization",
                ),
                Insight(
                    title="Critical Issue",
                    description="High priority",
                    confidence=0.95,
                    insight_type=InsightType.ANOMALY,
                    business_impact="CRITICAL: Fix immediately",
                ),
            ],
            recommendations=[],
        )

        actions = self.generator._extract_action_items(report)

        # First action should be CRITICAL
        assert actions[0]["priority"] == "CRITICAL"

    def test_action_items_limit_to_top_10(self):
        """Test that action items are limited to top 10."""
        insights = []
        for i in range(15):
            insights.append(
                Insight(
                    title=f"Issue {i}",
                    description=f"Description {i}",
                    confidence=0.7,
                    insight_type=InsightType.KEY_FINDING,
                    business_impact=f"ACTION: Fix issue {i}",
                )
            )

        report = AnalysisReport(
            title="Test Report",
            summary="",
            generated_at=datetime.now(),
            algorithm="wcc",
            dataset_info={"result_count": 100},
            insights=insights,
            recommendations=[],
        )

        actions = self.generator._extract_action_items(report)

        assert len(actions) <= 10


class TestReportMetadata:
    """Test that Phase 3 data is stored in report metadata."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = ReportGenerator(
            llm_provider=Mock(), use_llm_interpretation=False, enable_charts=False
        )

    def test_metadata_includes_risk_and_actions(self):
        """Test that generated reports include risk level and action items in metadata."""
        job = AnalysisJob(
            job_id="test-123",
            template_name="Test Template",
            algorithm="wcc",
            status=ExecutionStatus.COMPLETED,
            submitted_at=datetime.now(),
        )

        execution_result = ExecutionResult(
            job=job,
            success=True,
            results=[
                {"component": 1, "node": "A"},
                {"component": 1, "node": "B"},
                {"component": 2, "node": "C"},
            ],
        )

        report = self.generator.generate_report(execution_result)

        # Check metadata contains our Phase 3 additions
        assert "risk_level" in report.metadata
        assert "action_items" in report.metadata
        assert report.metadata["risk_level"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        assert isinstance(report.metadata["action_items"], list)
