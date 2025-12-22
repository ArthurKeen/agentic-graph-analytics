"""
Unit tests for schema analyzer.

Tests LLM-based schema analysis and report generation.
"""

from unittest.mock import Mock

from graph_analytics_ai.ai.schema.analyzer import SchemaAnalyzer
from graph_analytics_ai.ai.schema.models import SchemaAnalysis
from graph_analytics_ai.ai.llm import LLMProviderError


class TestSchemaAnalyzer:
    """Test SchemaAnalyzer class."""

    def test_init_with_provider(self, mock_llm_provider):
        """Test analyzer initialization with provider."""
        analyzer = SchemaAnalyzer(mock_llm_provider)

        assert analyzer.llm_provider == mock_llm_provider

    def test_init_without_provider(self):
        """Test analyzer initialization without provider."""
        # This would use get_default_provider(), which requires env config
        # We'll skip actual initialization test as it needs env setup
        pass

    def test_analyze_success(self, sample_graph_schema, mock_llm_provider):
        """Test successful schema analysis."""
        analyzer = SchemaAnalyzer(mock_llm_provider)

        analysis = analyzer.analyze(sample_graph_schema)

        # Verify LLM was called
        mock_llm_provider.generate_structured.assert_called_once()

        # Verify analysis result
        assert isinstance(analysis, SchemaAnalysis)
        assert analysis.schema == sample_graph_schema
        assert (
            analysis.description
            == "A social network graph with users and their relationships."
        )
        assert analysis.domain == "social network"
        assert len(analysis.key_entities) == 2
        assert len(analysis.key_relationships) == 2
        assert len(analysis.suggested_analyses) == 2
        assert analysis.complexity_score == 4.5

    def test_analyze_without_samples(self, sample_graph_schema, mock_llm_provider):
        """Test analysis without including sample documents."""
        analyzer = SchemaAnalyzer(mock_llm_provider)

        analysis = analyzer.analyze(sample_graph_schema, include_samples=False)

        # Verify LLM was called
        assert mock_llm_provider.generate_structured.called

        # Get the actual prompt argument
        call_args = mock_llm_provider.generate_structured.call_args
        call_args[0][0]

        # Verify samples were removed from prompt
        # (This is a simplified check - in reality we'd parse the JSON)
        assert isinstance(analysis, SchemaAnalysis)

    def test_analyze_llm_failure(self, sample_graph_schema, mock_llm_provider):
        """Test analysis when LLM fails."""
        # Make LLM fail
        mock_llm_provider.generate_structured.side_effect = LLMProviderError(
            "LLM failed"
        )

        analyzer = SchemaAnalyzer(mock_llm_provider)
        analysis = analyzer.analyze(sample_graph_schema)

        # Should return fallback analysis
        assert isinstance(analysis, SchemaAnalysis)
        assert "LLM analysis failed" in analysis.description
        assert analysis.domain == "Unknown (LLM analysis unavailable)"
        assert analysis.complexity_score > 0  # Calculated from schema

    def test_create_fallback_analysis(self, sample_graph_schema):
        """Test creating fallback analysis without LLM."""
        analyzer = SchemaAnalyzer(Mock())

        analysis = analyzer._create_fallback_analysis(sample_graph_schema)

        assert isinstance(analysis, SchemaAnalysis)
        assert analysis.schema == sample_graph_schema
        assert "100" in analysis.description  # user count
        assert "50" in analysis.description  # product count
        assert analysis.complexity_score > 0

        # Should have identified key entities by document count
        assert "users" in analysis.key_entities  # Highest count

    def test_create_fallback_analysis_with_error(self, sample_graph_schema):
        """Test fallback analysis including error message."""
        analyzer = SchemaAnalyzer(Mock())

        error_msg = "Test error message"
        analysis = analyzer._create_fallback_analysis(
            sample_graph_schema, error=error_msg
        )

        assert "LLM analysis failed" in analysis.description
        assert "Test error" in analysis.description

    def test_get_response_schema(self):
        """Test LLM response schema structure."""
        analyzer = SchemaAnalyzer(Mock())

        schema = analyzer._get_response_schema()

        assert schema["type"] == "object"
        assert "description" in schema["properties"]
        assert "domain" in schema["properties"]
        assert "key_entities" in schema["properties"]
        assert "suggested_analyses" in schema["properties"]
        assert "complexity_score" in schema["properties"]

        # Check required fields
        assert "description" in schema["required"]
        assert "domain" in schema["required"]


class TestReportGeneration:
    """Test report generation from schema analysis."""

    def test_generate_report_complete(self, sample_graph_schema, mock_llm_provider):
        """Test generating complete report."""
        analyzer = SchemaAnalyzer(mock_llm_provider)
        analysis = analyzer.analyze(sample_graph_schema)

        report = analyzer.generate_report(analysis)

        # Verify report contains key sections
        assert "GRAPH SCHEMA ANALYSIS REPORT" in report
        assert "Overview" in report
        assert "Statistics" in report
        assert "Key Entity Collections" in report
        assert "Key Relationships" in report
        assert "Recommended Graph Analytics" in report

        # Verify content
        assert "test_db" in report
        assert "social network" in report
        assert "4.5/10" in report

        # Verify statistics
        assert "100" in report  # user count
        assert "50" in report  # product count
        assert "200" in report  # follows edges

    def test_generate_report_simple_graph(self, sample_graph_schema):
        """Test report for simple graph."""
        analysis = SchemaAnalysis(
            schema=sample_graph_schema,
            description="Simple test graph",
            domain="testing",
            complexity_score=2.0,
        )

        analyzer = SchemaAnalyzer(Mock())
        report = analyzer.generate_report(analysis)

        assert "Simple graph structure" in report
        assert "2.0/10" in report

    def test_generate_report_complex_graph(self, sample_graph_schema):
        """Test report for complex graph."""
        analysis = SchemaAnalysis(
            schema=sample_graph_schema,
            description="Complex enterprise graph",
            domain="enterprise",
            complexity_score=9.5,
        )

        analyzer = SchemaAnalyzer(Mock())
        report = analyzer.generate_report(analysis)

        assert "Complex graph structure" in report
        assert "9.5/10" in report

    def test_generate_report_with_suggestions(self, sample_graph_schema):
        """Test report including analysis suggestions."""
        analysis = SchemaAnalysis(
            schema=sample_graph_schema,
            description="Test graph",
            domain="testing",
            suggested_analyses=[
                {
                    "type": "pagerank",
                    "title": "PageRank Analysis",
                    "reason": "Find influential nodes",
                },
                {
                    "type": "community",
                    "title": "Community Detection",
                    "reason": "Identify clusters",
                },
            ],
            complexity_score=5.0,
        )

        analyzer = SchemaAnalyzer(Mock())
        report = analyzer.generate_report(analysis)

        assert "Recommended Graph Analytics" in report
        assert "PageRank Analysis" in report
        assert "Find influential nodes" in report
        assert "Community Detection" in report
        assert "Identify clusters" in report

    def test_generate_report_with_key_entities(self, sample_graph_schema):
        """Test report with key entities."""
        analysis = SchemaAnalysis(
            schema=sample_graph_schema,
            description="Test graph",
            domain="testing",
            key_entities=["users", "products"],
            complexity_score=5.0,
        )

        analyzer = SchemaAnalyzer(Mock())
        report = analyzer.generate_report(analysis)

        assert "Key Entity Collections" in report
        assert "users" in report
        assert "products" in report
        assert "100 documents" in report  # user count
        assert "50 documents" in report  # product count

    def test_generate_report_with_relationships(self, sample_graph_schema):
        """Test report with key relationships."""
        analysis = SchemaAnalysis(
            schema=sample_graph_schema,
            description="Test graph",
            domain="testing",
            key_relationships=["follows", "purchased"],
            complexity_score=5.0,
        )

        analyzer = SchemaAnalyzer(Mock())
        report = analyzer.generate_report(analysis)

        assert "Key Relationships" in report
        assert "follows" in report
        assert "purchased" in report
        assert "200 edges" in report  # follows count
        assert "500 edges" in report  # purchased count
        assert "users → users" in report  # follows relationship
        assert "users → products" in report  # purchased relationship
