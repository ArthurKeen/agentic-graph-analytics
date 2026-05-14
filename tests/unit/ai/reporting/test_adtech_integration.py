"""
Integration test for ad-tech industry-specific reporting.

Tests the complete flow from execution results to report generation
with ad-tech specific prompts, validation, and insights.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from graph_analytics_ai.ai.reporting.generator import ReportGenerator
from graph_analytics_ai.ai.reporting.config import LLMReportingConfig
from graph_analytics_ai.ai.execution.models import (
    AnalysisJob,
    ExecutionResult,
    ExecutionStatus,
)


class TestAdTechIntegration:
    """Integration tests for ad-tech industry reporting."""

    def setup_method(self):
        """Setup test fixtures."""
        # Create generator with ad-tech industry
        self.generator = ReportGenerator(
            llm_provider=Mock(),
            use_llm_interpretation=False,  # Use heuristics for predictable testing
            enable_charts=False,
            industry="adtech",
        )

    def test_wcc_adtech_report_generation(self):
        """Test complete WCC report generation for ad-tech use case."""
        # Create job for household identity clustering
        job = AnalysisJob(
            job_id="adtech-wcc-001",
            template_name="UC-S01: Household Identity Clustering",
            algorithm="wcc",
            status=ExecutionStatus.COMPLETED,
            submitted_at=datetime.now(),
            result_count=1000,
        )

        # Simulate WCC results with ad-tech pattern (over-aggregation)
        results = []
        # Large component (potential over-aggregation)
        for i in range(570):
            results.append({"component": 1, "_key": f"Device/{i}"})
        # Singletons (fragmentation)
        for i in range(200):
            results.append({"component": i + 10, "_key": f"Device/{570 + i}"})
        # Small clusters
        for i in range(230):
            comp_id = (i // 3) + 300
            results.append({"component": comp_id, "_key": f"Device/{770 + i}"})

        execution_result = ExecutionResult(job=job, success=True, results=results)

        # Generate report
        report = self.generator.generate_report(execution_result)

        # Verify report structure
        assert report.title == "Analysis Report: UC-S01: Household Identity Clustering"
        assert report.algorithm == "wcc"
        assert len(report.insights) > 0

        # Verify insights are relevant to ad-tech
        insight_titles = " ".join([i.title for i in report.insights])
        # Should identify over-aggregation pattern
        assert any(
            keyword in insight_titles.lower()
            for keyword in ["aggregation", "cluster", "component", "concentration"]
        )

        # Verify metadata includes Phase 3 additions
        assert "risk_level" in report.metadata
        assert "action_items" in report.metadata

    def test_pagerank_adtech_report_generation(self):
        """Test complete PageRank report generation for ad-tech use case."""
        # Create job for inventory ranking
        job = AnalysisJob(
            job_id="adtech-pr-001",
            template_name="UC-S02: High-Value Inventory Ranking",
            algorithm="pagerank",
            status=ExecutionStatus.COMPLETED,
            submitted_at=datetime.now(),
            result_count=500,
        )

        # Simulate PageRank results with ad-tech pattern (concentration)
        results = []
        # Top node with high PageRank
        results.append({"_key": "Site/8448912", "result": 0.45})
        # Other high-ranking nodes
        for i in range(9):
            results.append({"_key": f"App/premium_{i}", "result": 0.05})
        # Long tail of low-ranking nodes
        for i in range(490):
            results.append({"_key": f"Site/site_{i}", "result": 0.001})

        execution_result = ExecutionResult(job=job, success=True, results=results)

        # Generate report
        report = self.generator.generate_report(execution_result)

        # Verify report structure
        assert report.algorithm == "pagerank"
        assert len(report.insights) > 0

        # Verify insights identify concentration
        insight_text = " ".join(
            [i.title + " " + i.description for i in report.insights]
        )
        assert any(
            keyword in insight_text.lower()
            for keyword in ["concentration", "top", "influence", "dominant"]
        )

    def test_adtech_validation_lenient_for_domain_terms(self):
        """Test that ad-tech validation is lenient with domain terminology."""
        # Create config with ad-tech settings
        config = LLMReportingConfig.for_industry("adtech")

        # Verify ad-tech specific settings
        assert config.industry == "adtech"
        assert config.min_confidence == 0.25  # Lower than generic (0.3)
        assert "botnet" in config.domain_specific_terms
        assert "household cluster" in config.domain_specific_terms
        assert "fraud" in config.domain_specific_terms

    def test_risk_assessment_for_fraud_pattern(self):
        """Test risk assessment correctly identifies fraud patterns."""
        # Create job
        job = AnalysisJob(
            job_id="fraud-test",
            template_name="Fraud Detection Test",
            algorithm="wcc",
            status=ExecutionStatus.COMPLETED,
            submitted_at=datetime.now(),
            result_count=100,
        )

        # Minimal results
        results = [{"component": 1, "_key": "Device/1"}]

        execution_result = ExecutionResult(job=job, success=True, results=results)

        # Generate report (will have heuristic insights)
        report = self.generator.generate_report(execution_result)

        # Manually add fraud insight to test risk assessment
        from graph_analytics_ai.ai.reporting.models import Insight, InsightType

        fraud_insight = Insight(
            title="Botnet Signature Detected at Component X",
            description="47 IPs connected to 127 devices indicating residential proxy network fraud pattern",
            confidence=0.88,
            insight_type=InsightType.ANOMALY,
            business_impact="IMMEDIATE: Block traffic. CRITICAL fraud risk.",
        )
        report.insights.append(fraud_insight)

        # Re-assess risk
        risk_level = self.generator._assess_risk_level(report.insights)

        # Should be CRITICAL due to botnet/fraud keywords
        assert risk_level == "CRITICAL"

    def test_action_items_extraction_from_adtech_insights(self):
        """Test action items are properly extracted from ad-tech specific insights."""
        # Create job
        job = AnalysisJob(
            job_id="action-test",
            template_name="Action Items Test",
            algorithm="wcc",
            status=ExecutionStatus.COMPLETED,
            submitted_at=datetime.now(),
            result_count=100,
        )

        results = [{"component": 1, "_key": "Device/1"}]

        execution_result = ExecutionResult(job=job, success=True, results=results)

        # Generate report
        report = self.generator.generate_report(execution_result)

        # Add ad-tech specific insight with action keywords
        from graph_analytics_ai.ai.reporting.models import Insight, InsightType

        insight = Insight(
            title="Over-Aggregation at Site/8448912",
            description="Single site bridging 570 devices across multiple DMAs",
            confidence=0.85,
            insight_type=InsightType.KEY_FINDING,
            business_impact="IMMEDIATE: Exclude Site nodes from clustering. RECOMMENDATION: Add secondary identity signals. Estimated impact: 15% accuracy improvement.",
        )
        report.insights.append(insight)

        # Extract action items
        actions = self.generator._extract_action_items(report)

        # Should extract both IMMEDIATE and RECOMMENDATION actions
        assert len(actions) >= 2
        priorities = [a["priority"] for a in actions]
        assert "IMMEDIATE" in priorities
        assert any(a["priority"] in ["MEDIUM", "RECOMMENDATION"] for a in actions)

        # Verify actions contain relevant content
        action_text = " ".join([a["action"] for a in actions])
        assert "Exclude Site nodes" in action_text or "identity signals" in action_text


class TestIndustryPromptIntegration:
    """Test that industry prompts are properly used."""

    def test_adtech_prompt_loaded(self):
        """Test that ad-tech prompt is loaded for generator."""
        from graph_analytics_ai.ai.reporting.prompts import get_industry_prompt

        adtech_prompt = get_industry_prompt("adtech")

        # Verify key ad-tech concepts are in prompt
        assert "botnet" in adtech_prompt.lower()
        assert "household" in adtech_prompt.lower()
        assert "fraud" in adtech_prompt.lower()
        assert "device" in adtech_prompt.lower()
        assert "ip" in adtech_prompt.lower() or "IP" in adtech_prompt

    def test_generic_prompt_fallback(self):
        """Test that generic prompt is used for unknown industries."""
        from graph_analytics_ai.ai.reporting.prompts import get_industry_prompt

        unknown_prompt = get_industry_prompt("unknown_industry_xyz")
        generic_prompt = get_industry_prompt("generic")

        # Should fall back to generic
        assert unknown_prompt == generic_prompt


class TestAlgorithmPatternDetection:
    """Test algorithm-specific pattern detection for ad-tech."""

    def test_wcc_pattern_detection_adtech(self):
        """Test WCC pattern detection for ad-tech."""
        from graph_analytics_ai.ai.reporting.algorithm_insights import detect_patterns

        # Simulate results with over-aggregation
        results = [{"component": 1, "_key": f"Node/{i}"} for i in range(570)]
        results += [
            {"component": i + 10, "_key": f"Node/{570 + i}"} for i in range(430)
        ]

        patterns = detect_patterns(
            algorithm="wcc", industry="adtech", results=results, total_nodes=1000
        )

        # Should detect over-aggregation pattern
        assert len(patterns) > 0
        pattern_types = [p["type"] for p in patterns]
        assert "over_aggregation" in pattern_types or "fragmentation" in pattern_types

    def test_pagerank_pattern_detection_adtech(self):
        """Test PageRank pattern detection for ad-tech."""
        from graph_analytics_ai.ai.reporting.algorithm_insights import detect_patterns

        # Simulate results with high concentration
        results = [
            {"_key": "Site/premium", "rank": 0.50},
            {"_key": "App/top1", "rank": 0.15},
            {"_key": "App/top2", "rank": 0.10},
        ]
        results += [{"_key": f"Site/site_{i}", "rank": 0.001} for i in range(97)]

        patterns = detect_patterns(
            algorithm="pagerank", industry="adtech", results=results
        )

        # Should detect concentration pattern
        assert len(patterns) > 0
        assert any("concentration" in p["type"] for p in patterns)
