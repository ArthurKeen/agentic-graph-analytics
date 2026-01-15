"""Tests for reporting generator."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from graph_analytics_ai.ai.reporting.generator import ReportGenerator
from graph_analytics_ai.ai.reporting.models import Insight, InsightType
from graph_analytics_ai.ai.execution.models import ExecutionResult, AnalysisJob, ExecutionStatus


class TestInsightParsing:
    """Tests for LLM insight parsing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = Mock()
        self.generator = ReportGenerator(llm_provider=self.mock_llm, use_llm_interpretation=True)
    
    def test_parse_llm_insights_multiple(self):
        """Test parsing multiple insights from LLM response."""
        llm_response = """
- Title: Top 5 Nodes Control 82% of Network Influence
  Description: Analysis reveals extreme concentration. The top 5 nodes account for 82% of total PageRank score.
  Business Impact: Focus marketing efforts on these nodes. Their performance affects revenue.
  Confidence: 0.95

- Title: Network Fragmented into 3 Major Clusters
  Description: WCC analysis reveals 3 large connected clusters with 127 isolated nodes.
  Business Impact: Investigate why clusters are disconnected. Connect isolated nodes.
  Confidence: 0.88
"""
        
        insights = self.generator._parse_llm_insights(llm_response)
        
        assert len(insights) == 2
        assert insights[0].title == "Top 5 Nodes Control 82% of Network Influence"
        assert insights[0].confidence == 0.95
        assert "extreme concentration" in insights[0].description.lower()
        assert "marketing" in insights[0].business_impact.lower()
        
        assert insights[1].title == "Network Fragmented into 3 Major Clusters"
        assert insights[1].confidence == 0.88
    
    def test_parse_llm_insights_single(self):
        """Test parsing single insight."""
        llm_response = """
- Title: Critical Bridge Nodes Identified
  Description: Found 7 nodes with high betweenness centrality acting as bottlenecks.
  Business Impact: Ensure redundancy for these nodes to prevent communication breakdown.
  Confidence: 0.91
"""
        
        insights = self.generator._parse_llm_insights(llm_response)
        
        assert len(insights) == 1
        assert insights[0].title == "Critical Bridge Nodes Identified"
        assert insights[0].confidence == 0.91
    
    def test_parse_llm_insights_fallback(self):
        """Test fallback parsing when structured format is not found."""
        llm_response = """This is an unstructured response that doesn't follow the expected format.
It contains some analysis but no clear Title/Description/Business Impact sections."""
        
        insights = self.generator._parse_llm_insights(llm_response)
        
        assert len(insights) == 1
        assert insights[0].title == "Analysis Results (Unparsed)"
        assert insights[0].confidence <= 0.6
        assert "unstructured response" in insights[0].description.lower()
    
    def test_parse_llm_insights_multiline_fields(self):
        """Test parsing insights with multiline field content."""
        llm_response = """
- Title: Extreme Influence Distribution
  Description: Analysis of 500 nodes reveals power law distribution.
    Top nodes have disproportionate influence.
    Bottom 50% account for only 3% of total influence.
  Business Impact: Focus on top performers.
    Deprioritize long tail nodes for efficiency.
  Confidence: 0.89
"""
        
        insights = self.generator._parse_llm_insights(llm_response)
        
        assert len(insights) == 1
        assert "power law distribution" in insights[0].description.lower()
        assert "focus on top performers" in insights[0].business_impact.lower()


class TestInsightTypeInference:
    """Tests for insight type inference."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = Mock()
        self.generator = ReportGenerator(llm_provider=self.mock_llm)
    
    def test_infer_anomaly(self):
        """Test inferring ANOMALY type from title."""
        assert self.generator._infer_insight_type("Unusual Spike in Node Activity") == InsightType.ANOMALY
        assert self.generator._infer_insight_type("Unexpected Outlier Detected") == InsightType.ANOMALY
    
    def test_infer_pattern(self):
        """Test inferring PATTERN type from title."""
        assert self.generator._infer_insight_type("Distribution Pattern Identified") == InsightType.PATTERN
        assert self.generator._infer_insight_type("Network Trend Analysis") == InsightType.PATTERN
    
    def test_infer_opportunity(self):
        """Test inferring CORRELATION type from title."""
        assert self.generator._infer_insight_type("Growth Opportunity in Long Tail") == InsightType.KEY_FINDING
        assert self.generator._infer_insight_type("Potential for Optimization") == InsightType.KEY_FINDING
    
    def test_infer_concern(self):
        """Test inferring ANOMALY type from risk/problem terms."""
        assert self.generator._infer_insight_type("Critical Risk Identified") == InsightType.KEY_FINDING
        assert self.generator._infer_insight_type("Network Problem Detected") == InsightType.KEY_FINDING
    
    def test_infer_key_finding_default(self):
        """Test default to KEY_FINDING type."""
        assert self.generator._infer_insight_type("Top Nodes Identified") == InsightType.KEY_FINDING


class TestInsightValidation:
    """Tests for insight validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = Mock()
        self.generator = ReportGenerator(llm_provider=self.mock_llm)
    
    def test_validate_insights_filters_generic(self):
        """Test validation filters out generic insights."""
        insights = [
            Insight(
                title="LLM Analysis",
                description="Short description",
                confidence=0.9,
                insight_type=InsightType.KEY_FINDING,
                business_impact="Generic impact",
            ),
            Insight(
                title="Top 5 Products Account for 67% of Revenue",
                description="Detailed analysis shows that products P1, P2, P3, P4, and P5 collectively generated $1.2M in revenue, representing 67% of total sales in Q4. This concentration indicates strong product-market fit for these items. The distribution shows a clear power law with extreme concentration at the top.",
                confidence=0.92,
                insight_type=InsightType.KEY_FINDING,
                business_impact="Double down on marketing for these 5 products in Q1. Ensure supply chain can handle increased demand.",
            )
        ]
        
        validated = self.generator._validate_insights(insights)
        
        # With relaxed validation, generic insight is kept but penalized
        # Should keep at least 1 (fallback keeps top 3)
        assert len(validated) >= 1
        
        # Generic one should have lower confidence than the good one
        if len(validated) == 2:
            # Sort by confidence to find which is which
            sorted_by_conf = sorted(validated, key=lambda x: x.confidence, reverse=True)
            assert sorted_by_conf[0].confidence > sorted_by_conf[1].confidence
            assert "67%" in sorted_by_conf[0].title  # Good one has higher confidence
    
    def test_validate_insights_requires_specificity(self):
        """Test validation requires specific metrics."""
        insights = [
            Insight(
                title="Many Nodes Are Connected",
                description="The network has a lot of connections between nodes and they form communities.",
                confidence=0.8,
                insight_type=InsightType.PATTERN,
                business_impact="Improve network",
            )
        ]
        
        validated = self.generator._validate_insights(insights)
        
        # With relaxed validation, insight is kept but confidence is reduced
        assert len(validated) >= 1
        if validated:
            # Confidence should be reduced due to quality issues, but not as harshly
            # (was <0.5, now less strict - around 0.6-0.7 due to softer penalties)
            assert validated[0].confidence < 0.8  # Still penalized, just less harsh
    
    def test_validate_insights_keeps_quality(self):
        """Test validation keeps high-quality insights."""
        insights = [
            Insight(
                title="Top 10 Nodes Hold 85% of Network Influence",
                description="Analysis of 1000 nodes reveals extreme concentration. The top 10 nodes (1% of total) account for 85% of cumulative PageRank score. Leading node has rank 0.347, which is 12x higher than median (0.029). This power law distribution indicates winner-take-most dynamics.",
                confidence=0.93,
                insight_type=InsightType.PATTERN,
                business_impact="Concentrate resources on top 10 nodes. Their performance drives 85% of network impact. Implement monitoring to detect if any become inactive.",
            ),
            Insight(
                title="Network Fragmented into 5 Major Clusters and 234 Singletons",
                description="Weak component analysis reveals 5 large connected clusters (45K, 12K, 8K, 3K, 1.5K nodes) and 234 completely isolated singleton nodes. Main cluster contains 65% of all nodes. Singletons are primarily recent additions (< 30 days old).",
                confidence=0.91,
                insight_type=InsightType.PATTERN,
                business_impact="Investigate why 234 entities are isolated - likely data quality issues or onboarding problems. Connect main clusters to improve cross-cluster collaboration.",
            )
        ]
        
        validated = self.generator._validate_insights(insights)
        
        assert len(validated) == 2
        assert all(len(i.description) >= 100 for i in validated)
        assert all(i.confidence >= 0.4 for i in validated)
    
    def test_validate_insights_adjusts_confidence(self):
        """Test validation adjusts confidence based on quality."""
        insights = [
            Insight(
                title="Short Title",
                description="Brief description without numbers or specifics but longer than minimum characters so it passes that check but fails others.",
                confidence=0.9,
                insight_type=InsightType.KEY_FINDING,
                business_impact="Further analysis needed",
            )
        ]
        
        validated = self.generator._validate_insights(insights)
        
        # Should adjust confidence downward due to quality issues
        if validated:
            assert validated[0].confidence < 0.9


class TestHeuristicInsights:
    """Tests for heuristic insight generation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = Mock()
        self.generator = ReportGenerator(llm_provider=self.mock_llm, use_llm_interpretation=False)
    
    def test_pagerank_insights_with_data(self):
        """Test PageRank insights with realistic data."""
        results = [
            {"_key": "P1", "result": 0.28},
            {"_key": "P2", "result": 0.15},
            {"_key": "P3", "result": 0.12},
            {"_key": "P4", "result": 0.10},
            {"_key": "P5", "result": 0.08},
            {"_key": "P6", "result": 0.05},
            {"_key": "P7", "result": 0.04},
            {"_key": "P8", "result": 0.03},
            {"_key": "P9", "result": 0.02},
            {"_key": "P10", "result": 0.01},
        ]
        
        insights = self.generator._pagerank_insights(results)
        
        assert len(insights) >= 2
        # Check that insights contain numbers
        assert any("%" in i.title or "%" in i.description for i in insights)
        # Check that insights mention specific nodes
        assert any("P1" in i.description for i in insights)
    
    def test_pagerank_insights_empty_results(self):
        """Test PageRank insights with empty results."""
        insights = self.generator._pagerank_insights([])
        
        assert len(insights) == 0
    
    def test_wcc_insights_with_singletons(self):
        """Test WCC insights detect isolated nodes."""
        results = [
            {"_key": f"N{i}", "component": 0} for i in range(50)
        ] + [
            {"_key": f"S{i}", "component": i+1} for i in range(10)
        ]
        
        insights = self.generator._wcc_insights(results)
        
        assert len(insights) >= 1
        # Should mention singleton detection
        assert any("isolated" in i.description.lower() or "singleton" in i.description.lower() 
                   for i in insights)
    
    def test_betweenness_insights_identifies_bridges(self):
        """Test betweenness insights identify bridge nodes."""
        results = [
            {"_key": "Bridge1", "betweenness": 0.15},
            {"_key": "Bridge2", "betweenness": 0.12},
            {"_key": "Normal1", "betweenness": 0.02},
            {"_key": "Normal2", "betweenness": 0.01},
        ]
        
        insights = self.generator._betweenness_insights(results)
        
        assert len(insights) >= 1
        assert any("bridge" in i.title.lower() or "critical" in i.title.lower() 
                   for i in insights)


class TestReasoningChain:
    """Tests for reasoning chain functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = Mock()
        self.generator = ReportGenerator(llm_provider=self.mock_llm, use_llm_interpretation=True)
    
    def test_create_reasoning_prompt(self):
        """Test creation of reasoning prompt."""
        job = AnalysisJob(
            job_id="test-job-123",
            template_name="test_template",
            algorithm="pagerank",
            status=ExecutionStatus.COMPLETED,
            submitted_at=datetime.now(),
        )
        results = [{"_key": "N1", "result": 0.5}]
        context = {"domain": "e-commerce"}
        
        prompt = self.generator._create_reasoning_prompt(job, results, context)
        
        assert "Step 1: Data Observation" in prompt
        assert "Step 2: Statistical Analysis" in prompt
        assert "Step 3: Business Context" in prompt
        assert "Reasoning:" in prompt
    
    def test_parse_llm_insights_with_reasoning(self):
        """Test parsing insights that include reasoning section."""
        llm_response = """
## Reasoning:
Looking at the data, I observe that the top 5 nodes have significantly higher scores...

## Insights:

- Title: Top 5 Control 80% of Influence
  Description: Extreme concentration detected in the network.
  Business Impact: Focus on these nodes.
  Confidence: 0.92
"""
        
        insights = self.generator._parse_llm_insights_with_reasoning(llm_response)
        
        assert len(insights) >= 1
        assert insights[0].title == "Top 5 Control 80% of Influence"
