"""
Tests for Phase 1 parsing improvements: numbered sections and reformat fallback.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from graph_analytics_ai.ai.reporting.generator import ReportGenerator
from graph_analytics_ai.ai.reporting.models import Insight, InsightType
from graph_analytics_ai.ai.llm.base import LLMResponse


class TestNumberedSectionsParsing:
    """Test parsing of '# Insight 1 (PageRank):' format."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = ReportGenerator(
            llm_provider=Mock(), use_llm_interpretation=False
        )

    def test_parse_numbered_sections_single_insight(self):
        """Test parsing single numbered insight."""
        llm_response = """
# Insight 1 (PageRank):
- **Title: Site/8448912 Emerges as Central Hub**
  **Description**: Analysis shows that Site/8448912 has the highest PageRank score of 0.94, 
  indicating it is the most influential node in the network.
  **Business Impact**: Focus marketing efforts on this high-value site.
  **Confidence**: 0.94
"""

        insights = self.generator._parse_numbered_sections(llm_response)

        assert len(insights) == 1
        assert "Site/8448912" in insights[0].title
        assert "Central Hub" in insights[0].title
        assert (
            "0.94" in insights[0].description
            or "highest PageRank" in insights[0].description
        )
        assert insights[0].confidence >= 0.9

    def test_parse_numbered_sections_multiple_insights(self):
        """Test parsing multiple numbered insights."""
        llm_response = """
# Insight 1 (PageRank):
- **Title: Top Node Has 80% Concentration**
  **Description**: The leading node accounts for 80% of total influence.
  **Business Impact**: This is a critical hub for the network.
  **Confidence**: 0.92

# Insight 2 (PageRank):
- **Title: IP Addresses Dominate Rankings**
  **Description**: 7 out of 10 top nodes are IP addresses rather than devices.
  **Business Impact**: Validate data quality - IPs should not outrank devices.
  **Confidence**: 0.75
"""

        insights = self.generator._parse_numbered_sections(llm_response)

        assert len(insights) == 2
        assert "80% Concentration" in insights[0].title
        assert "IP Addresses" in insights[1].title
        assert insights[0].confidence >= 0.9
        assert insights[1].confidence >= 0.7

    def test_parse_numbered_sections_with_multiline_description(self):
        """Test parsing with multiline descriptions."""
        llm_response = """
# Insight 1 (WCC):
- **Title: Botnet Signature Detected**
  **Description**: Component Site/8448912 exhibits classic botnet pattern with 47 unique IPs 
  connected to 127 devices. Normal households show 1-3 IPs per 5-15 devices. This component 
  shows 15:1 IP-to-device ratio, indicating residential proxy network.
  **Business Impact**: IMMEDIATE: Block traffic from component Site/8448912. Estimated risk: $12-18K/month.
  **Confidence**: 0.87
"""

        insights = self.generator._parse_numbered_sections(llm_response)

        assert len(insights) == 1
        assert "Botnet" in insights[0].title
        assert "47 unique IPs" in insights[0].description
        assert "127 devices" in insights[0].description
        assert "IMMEDIATE" in insights[0].business_impact
        assert insights[0].confidence >= 0.85

    def test_parse_numbered_sections_missing_fields(self):
        """Test parsing with some fields missing."""
        llm_response = """
# Insight 1:
- **Title: Incomplete Insight**
  **Description**: Only has title and description.
"""

        insights = self.generator._parse_numbered_sections(llm_response)

        # Should still create insight with defaults for missing fields
        assert len(insights) == 1
        assert insights[0].title == "Incomplete Insight"
        assert insights[0].description == "Only has title and description."

    def test_parse_numbered_sections_empty_response(self):
        """Test parsing empty response."""
        llm_response = ""

        insights = self.generator._parse_numbered_sections(llm_response)

        assert len(insights) == 0

    def test_parse_numbered_sections_no_match(self):
        """Test parsing with no numbered sections."""
        llm_response = "This is just plain text without any numbered insights."

        insights = self.generator._parse_numbered_sections(llm_response)

        assert len(insights) == 0


class TestReformatAndParse:
    """Test LLM reformatting fallback."""

    def setup_method(self):
        """Setup test fixtures."""
        mock_llm = Mock()
        self.generator = ReportGenerator(
            llm_provider=mock_llm, use_llm_interpretation=False
        )
        self.mock_llm = mock_llm

    def test_reformat_and_parse_success(self):
        """Test successful reformatting by LLM."""
        # Setup mock LLM to return properly formatted response
        self.mock_llm.generate.return_value = LLMResponse(
            content="""
- Title: Reformatted Insight
  Description: The LLM successfully reformatted this insight into the expected structure.
  Business Impact: This demonstrates the fallback mechanism works.
  Confidence: 0.80
""",
            total_tokens=100,
        )

        messy_response = """
The analysis shows that there's a problem with the network. 
It seems like there are too many connections in one place.
We should probably do something about it.
"""

        insights = self.generator._reformat_and_parse(messy_response)

        # Should have called LLM to reformat
        assert self.mock_llm.generate.called
        assert len(insights) >= 1
        if insights:
            assert insights[0].title == "Reformatted Insight"

    def test_reformat_and_parse_llm_failure(self):
        """Test handling of LLM failure during reformatting."""
        # Setup mock LLM to raise exception
        self.mock_llm.generate.side_effect = Exception("LLM API error")

        messy_response = "Some unstructured text"

        insights = self.generator._reformat_and_parse(messy_response)

        # Should return empty list on failure
        assert insights == []

    def test_reformat_and_parse_preserves_content_length(self):
        """Test that reformatting truncates long responses."""
        # Long response > 2000 chars
        long_response = "This is a very long response. " * 100

        self.mock_llm.generate.return_value = LLMResponse(
            content="- Title: Test\n  Description: Short\n  Business Impact: Impact\n  Confidence: 0.5",
            total_tokens=50,
        )

        self.generator._reformat_and_parse(long_response)

        # Check that the call to LLM had truncated content
        call_args = self.mock_llm.generate.call_args
        assert (
            len(call_args[1]["prompt"]) < 2500
        )  # Prompt includes instructions + truncated content


class TestParsingFallbackChain:
    """Test the complete parsing fallback chain."""

    def setup_method(self):
        """Setup test fixtures."""
        mock_llm = Mock()
        self.generator = ReportGenerator(
            llm_provider=mock_llm, use_llm_interpretation=False
        )
        self.mock_llm = mock_llm

    def test_fallback_chain_structured_format_succeeds(self):
        """Test that structured format is tried first."""
        response = """
- Title: Structured Format Test
  Description: This uses the standard structured format.
  Business Impact: Should parse on first attempt.
  Confidence: 0.85
"""

        insights = self.generator._parse_llm_insights(response)

        # Should parse successfully without needing fallbacks
        assert len(insights) == 1
        assert insights[0].title == "Structured Format Test"
        # LLM should NOT have been called for reformatting
        assert not self.mock_llm.generate.called

    def test_fallback_chain_numbered_sections_succeeds(self):
        """Test that numbered sections format is tried second."""
        response = """
# Insight 1 (Algorithm):
- **Title: Numbered Section Format**
  **Description**: Uses numbered sections with markdown.
  **Business Impact**: Should parse on second attempt.
  **Confidence**: 0.80
"""

        insights = self.generator._parse_llm_insights(response)

        # Should parse via numbered sections
        assert len(insights) == 1
        assert "Numbered Section Format" in insights[0].title
        # LLM should NOT have been called for reformatting
        assert not self.mock_llm.generate.called

    def test_fallback_chain_reformat_succeeds(self):
        """Test that LLM reformatting is tried third."""
        messy_response = (
            "Just some unstructured analysis text without proper formatting."
        )

        # Mock LLM to return proper format
        self.mock_llm.generate.return_value = LLMResponse(
            content="""
- Title: Reformatted by LLM
  Description: The LLM fixed the formatting.
  Business Impact: Third fallback worked.
  Confidence: 0.70
""",
            total_tokens=80,
        )

        insights = self.generator._parse_llm_insights(messy_response)

        # Should have tried reformatting
        assert self.mock_llm.generate.called
        assert len(insights) >= 1

    def test_fallback_chain_final_fallback(self):
        """Test that final fallback creates generic insight."""
        messy_response = "Completely unparseable content that can't be fixed."

        # Mock LLM to fail
        self.mock_llm.generate.side_effect = Exception("API error")

        insights = self.generator._parse_llm_insights(messy_response)

        # Should create generic fallback insight
        assert len(insights) == 1
        assert "Unparsed" in insights[0].title
        assert insights[0].confidence <= 0.6
        assert "unparseable content" in insights[0].description.lower()


class TestStructuredFormatParsing:
    """Test the _parse_structured_format method directly."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = ReportGenerator(
            llm_provider=Mock(), use_llm_interpretation=False
        )

    def test_parse_structured_format_basic(self):
        """Test basic structured format parsing."""
        response = """
- Title: Basic Test
  Description: Simple description.
  Business Impact: Some impact.
  Confidence: 0.75
"""

        insights = self.generator._parse_structured_format(response)

        assert len(insights) == 1
        assert insights[0].title == "Basic Test"
        assert insights[0].confidence == 0.75

    def test_parse_structured_format_with_numbers(self):
        """Test parsing with numbered bullets."""
        response = """
1. Title: Numbered Item
   Description: Uses numbers instead of dashes.
   Business Impact: Should still parse.
   Confidence: 0.65
"""

        insights = self.generator._parse_structured_format(response)

        assert len(insights) == 1
        assert "Numbered Item" in insights[0].title

    def test_parse_structured_format_multiline_continuation(self):
        """Test parsing with multiline field continuation."""
        response = """
- Title: Multiline Test
  Description: This is a long description
  that continues on multiple lines
  without field markers.
  Business Impact: Should combine all lines
  into the description field.
  Confidence: 0.80
"""

        insights = self.generator._parse_structured_format(response)

        assert len(insights) == 1
        assert "multiple lines" in insights[0].description
        assert "combine all lines" in insights[0].business_impact
