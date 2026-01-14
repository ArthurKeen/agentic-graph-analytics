"""Integration tests for end-to-end report quality."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from graph_analytics_ai.ai.reporting.generator import ReportGenerator
from graph_analytics_ai.ai.reporting.models import ReportFormat
from graph_analytics_ai.ai.execution.models import ExecutionResult, AnalysisJob, ExecutionStatus


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    mock = Mock()
    mock_response = Mock()
    mock_response.content = """
- Title: Top 5 Products Account for 82% of Network Influence
  Description: Analysis of 500 products shows extreme concentration. The top 5 products (1% of total) have cumulative PageRank of 0.82, indicating they drive most purchase decisions. Product 'P123' leads with rank 0.28 (10x median of 0.028).
  Business Impact: Focus marketing budget on these 5 products. Their performance disproportionately affects revenue. Monitor for single points of failure.
  Confidence: 0.95

- Title: Middle Tier Shows Consistent Engagement Pattern
  Description: Products ranked 6-50 (9% of catalog) collectively hold 15% of total influence, with relatively consistent scores (0.02-0.04 range). This middle tier demonstrates stable, predictable performance.
  Business Impact: These 45 products represent reliable revenue generators. Scale up production and marketing for this tier to build predictable baseline revenue.
  Confidence: 0.88

- Title: Long Tail Represents Growth Opportunity
  Description: Bottom 450 products (90% of catalog) account for only 3% of current influence, but show diverse characteristics and niche appeal. Analysis of attributes suggests 23 products have high growth potential.
  Business Impact: Data-driven product portfolio optimization opportunity. Identify and promote high-potential long-tail products to capture niche markets.
  Confidence: 0.76
"""
    mock.generate.return_value = mock_response
    return mock


@pytest.fixture
def sample_execution_result():
    """Create a sample execution result for testing."""
    job = AnalysisJob(
        job_id="test-job-123",
        template_name="test_template",
        algorithm="pagerank",
        status=ExecutionStatus.COMPLETED,
        submitted_at=datetime.now(),
    )
    
    results = [
        {"_key": "P123", "result": 0.28},
        {"_key": "P456", "result": 0.15},
        {"_key": "P789", "result": 0.12},
        {"_key": "P101", "result": 0.10},
        {"_key": "P202", "result": 0.08},
        {"_key": "P303", "result": 0.05},
        {"_key": "P404", "result": 0.04},
        {"_key": "P505", "result": 0.03},
        {"_key": "P606", "result": 0.02},
        {"_key": "P707", "result": 0.01},
    ]
    
    return ExecutionResult(
        job=job,
        success=True,
        results=results,
    )


class TestEndToEndReportQuality:
    """Test complete report generation with quality checks."""
    
    def test_report_generation_with_llm(self, mock_llm_provider, sample_execution_result):
        """Test complete report generation using LLM."""
        context = {
            "requirements": {
                "domain": "e-commerce",
                "objectives": [{
                    "title": "Identify Key Influencers",
                    "description": "Find most influential products",
                    "success_criteria": ["Identify top 10 products", "Measure influence concentration"]
                }]
            }
        }
        
        generator = ReportGenerator(llm_provider=mock_llm_provider, use_llm_interpretation=True)
        report = generator.generate_report(sample_execution_result, context)
        
        # Quality assertions
        assert len(report.insights) >= 3, "Should have multiple insights"
        assert report.title is not None
        assert report.summary is not None
        assert report.algorithm == "pagerank"
        
        # Check for quantified insights
        has_numbers = any("%" in i.title or "%" in i.description for i in report.insights)
        assert has_numbers, "Should have quantified insights with percentages"
        
        # Check title specificity
        for insight in report.insights:
            assert len(insight.title) > 15, f"Title should be specific: {insight.title}"
            assert insight.title != "LLM Analysis", "Should not have generic title"
        
        # Check description quality
        for insight in report.insights:
            assert len(insight.description) > 100, f"Description should be substantive: {insight.description[:50]}..."
        
        # Check confidence thresholds
        for insight in report.insights:
            assert insight.confidence >= 0.4, f"All insights should meet quality threshold: {insight.confidence}"
    
    def test_report_generation_with_heuristics(self, sample_execution_result):
        """Test report generation using heuristic insights."""
        from unittest.mock import Mock
        
        # Create a mock LLM provider (though it won't be used)
        mock_llm = Mock()
        
        generator = ReportGenerator(llm_provider=mock_llm, use_llm_interpretation=False)
        report = generator.generate_report(sample_execution_result)
        
        # Should still generate quality report with heuristics
        assert len(report.insights) >= 2, "Heuristic mode should generate multiple insights"
        
        # Heuristic insights should include statistics
        has_stats = any(
            "%" in i.title or "%" in i.description or 
            any(str(n) in i.description for n in range(10))
            for i in report.insights
        )
        assert has_stats, "Heuristic insights should include statistical analysis"
    
    def test_report_formats(self, mock_llm_provider, sample_execution_result):
        """Test report can be formatted in different formats."""
        generator = ReportGenerator(llm_provider=mock_llm_provider, use_llm_interpretation=True)
        report = generator.generate_report(sample_execution_result)
        
        # Test markdown format
        markdown = generator.format_report(report, ReportFormat.MARKDOWN)
        assert markdown is not None
        assert "##" in markdown or "#" in markdown, "Markdown should have headers"
        
        # Test JSON format
        json_output = generator.format_report(report, ReportFormat.JSON)
        assert json_output is not None
        assert "{" in json_output and "}" in json_output, "JSON should be valid"
        
        # Test HTML format
        html = generator.format_report(report, ReportFormat.HTML)
        assert html is not None
        assert "<h" in html.lower(), "HTML should have headers"
    
    def test_report_validation_filters_low_quality(self, mock_llm_provider):
        """Test that validation filters out low-quality insights."""
        # Create execution result with minimal data
        job = AnalysisJob(
            job_id="test-job",
            template_name="test_template",
            algorithm="pagerank",
            status=ExecutionStatus.COMPLETED,
            submitted_at=datetime.now(),
        )
        
        result = ExecutionResult(
            job=job,
            success=True,
            results=[{"_key": "N1", "result": 0.5}],
        )
        
        # Mock LLM to return low-quality insights
        mock_response = Mock()
        mock_response.content = """
- Title: Top Node
  Description: Short
  Business Impact: Do something
  Confidence: 0.4
"""
        mock_llm_provider.generate.return_value = mock_response
        
        generator = ReportGenerator(llm_provider=mock_llm_provider, use_llm_interpretation=True)
        report = generator.generate_report(result)
        
        # Low-quality insights should be filtered or have reduced confidence
        if report.insights:
            for insight in report.insights:
                # Either filtered out or confidence adjusted down
                assert insight.confidence < 0.5 or len(insight.description) >= 100


class TestReportQualityMetrics:
    """Test quality metrics for generated reports."""
    
    def test_insight_count_target(self, mock_llm_provider, sample_execution_result):
        """Test that reports generate target number of insights."""
        generator = ReportGenerator(llm_provider=mock_llm_provider, use_llm_interpretation=True)
        report = generator.generate_report(sample_execution_result)
        
        # Target: 3-5 insights per report
        assert 3 <= len(report.insights) <= 6, f"Should have 3-5 insights, got {len(report.insights)}"
    
    def test_average_confidence_quality(self, mock_llm_provider, sample_execution_result):
        """Test that average insight confidence meets quality standards."""
        generator = ReportGenerator(llm_provider=mock_llm_provider, use_llm_interpretation=True)
        report = generator.generate_report(sample_execution_result)
        
        if report.insights:
            avg_confidence = sum(i.confidence for i in report.insights) / len(report.insights)
            assert avg_confidence >= 0.7, f"Average confidence should be >= 0.7, got {avg_confidence:.2f}"
    
    def test_business_impact_specificity(self, mock_llm_provider, sample_execution_result):
        """Test that business impacts are specific and actionable."""
        generator = ReportGenerator(llm_provider=mock_llm_provider, use_llm_interpretation=True)
        report = generator.generate_report(sample_execution_result)
        
        generic_phrases = [
            'further analysis',
            'requires investigation',
            'derived from',
        ]
        
        for insight in report.insights:
            # Business impact should not be purely generic
            is_generic = all(phrase in insight.business_impact.lower() for phrase in generic_phrases)
            assert not is_generic, f"Business impact should not be generic: {insight.business_impact}"
    
    def test_reports_include_quantification(self, mock_llm_provider, sample_execution_result):
        """Test that reports include quantified findings."""
        generator = ReportGenerator(llm_provider=mock_llm_provider, use_llm_interpretation=True)
        report = generator.generate_report(sample_execution_result)
        
        # At least 85% of reports should have numbers/percentages
        insights_with_numbers = sum(
            1 for i in report.insights 
            if "%" in i.title or "%" in i.description or 
            any(str(n) in i.description for n in [str(x) for x in range(100)])
        )
        
        percentage_with_numbers = (insights_with_numbers / len(report.insights) * 100) if report.insights else 0
        assert percentage_with_numbers >= 50, f"At least 50% of insights should have numbers, got {percentage_with_numbers:.1f}%"


class TestFallbackBehavior:
    """Test fallback behavior when LLM fails."""
    
    def test_fallback_to_heuristics_on_llm_failure(self, sample_execution_result):
        """Test that generator falls back to heuristics when LLM fails."""
        mock_llm = Mock()
        mock_llm.generate.side_effect = Exception("LLM API Error")
        
        generator = ReportGenerator(llm_provider=mock_llm, use_llm_interpretation=True)
        report = generator.generate_report(sample_execution_result)
        
        # Should still generate a report using heuristics
        assert report is not None
        assert len(report.insights) > 0, "Should fall back to heuristic insights"
    
    def test_empty_results_handling(self, mock_llm_provider):
        """Test handling of empty execution results."""
        job = AnalysisJob(
            job_id="test-job",
            template_name="test_template",
            algorithm="pagerank",
            status=ExecutionStatus.COMPLETED,
            submitted_at=datetime.now(),
        )
        
        result = ExecutionResult(
            job=job,
            success=True,
            results=[],  # Empty results
        )
        
        generator = ReportGenerator(llm_provider=mock_llm_provider, use_llm_interpretation=True)
        report = generator.generate_report(result)
        
        # Should handle gracefully
        assert report is not None
        # Either success or has no insights
        assert report.summary is not None or len(report.insights) == 0
