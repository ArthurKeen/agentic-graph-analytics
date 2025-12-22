"""
Unit tests for requirements extractor.

Tests LLM-based requirements extraction from documents.
"""

from unittest.mock import Mock

from graph_analytics_ai.ai.documents.extractor import RequirementsExtractor
from graph_analytics_ai.ai.documents.models import (
    ExtractedRequirements,
    RequirementType,
    Priority,
)
from graph_analytics_ai.ai.llm import LLMProviderError


class TestRequirementsExtractor:
    """Test RequirementsExtractor class."""

    def test_init_with_provider(self, mock_llm_provider):
        """Test extractor initialization with provider."""
        extractor = RequirementsExtractor(mock_llm_provider)

        assert extractor.llm_provider == mock_llm_provider
        assert extractor.max_content_length > 0

    def test_extract_success(self, sample_document, mock_llm_provider):
        """Test successful requirements extraction."""
        extractor = RequirementsExtractor(mock_llm_provider)

        extracted = extractor.extract([sample_document])

        # Verify LLM was called
        mock_llm_provider.generate_structured.assert_called_once()

        # Verify extraction result
        assert isinstance(extracted, ExtractedRequirements)
        assert extracted.domain == "e-commerce"
        assert len(extracted.requirements) == 2
        assert len(extracted.stakeholders) == 2
        assert len(extracted.objectives) == 1
        assert len(extracted.constraints) == 2

    def test_extract_multiple_documents(self, sample_document, mock_llm_provider):
        """Test extracting from multiple documents."""
        extractor = RequirementsExtractor(mock_llm_provider)

        # Create second document
        doc2 = type(
            "Document",
            (),
            {
                "metadata": type(
                    "Metadata",
                    (),
                    {
                        "file_name": "doc2.txt",
                        "document_type": type("DocType", (), {"value": "text"})(),
                    },
                )(),
                "word_count": 100,
                "content": "Additional requirements document",
            },
        )()

        extracted = extractor.extract([sample_document, doc2])

        assert len(extracted.documents) == 2
        assert extracted.total_requirements > 0

    def test_format_documents(self, sample_document):
        """Test document formatting for LLM prompt."""
        extractor = RequirementsExtractor(Mock())

        formatted = extractor._format_documents([sample_document])

        assert sample_document.metadata.file_name in formatted
        assert sample_document.content in formatted
        assert "Document 1:" in formatted

    def test_truncate_long_content(self, sample_document, mock_llm_provider):
        """Test content truncation for long documents."""
        # Create very long document
        long_content = "x" * 100000
        sample_document.content = long_content

        extractor = RequirementsExtractor(mock_llm_provider, max_content_length=1000)

        formatted = extractor._format_documents([sample_document])

        assert len(formatted) <= 1100  # Some overhead for formatting
        assert "[... content truncated ...]" in formatted

    def test_parse_requirement_type(self):
        """Test parsing requirement types."""
        extractor = RequirementsExtractor(Mock())

        test_cases = [
            ("functional", RequirementType.FUNCTIONAL),
            ("non_functional", RequirementType.NON_FUNCTIONAL),
            ("business", RequirementType.BUSINESS),
            ("technical", RequirementType.TECHNICAL),
            ("constraint", RequirementType.CONSTRAINT),
            ("objective", RequirementType.OBJECTIVE),
            ("unknown", RequirementType.BUSINESS),  # default
        ]

        for input_str, expected_type in test_cases:
            result = extractor._parse_requirement_type(input_str)
            assert result == expected_type

    def test_parse_priority(self):
        """Test parsing priority levels."""
        extractor = RequirementsExtractor(Mock())

        test_cases = [
            ("critical", Priority.CRITICAL),
            ("high", Priority.HIGH),
            ("medium", Priority.MEDIUM),
            ("low", Priority.LOW),
            ("unknown", Priority.UNKNOWN),  # default
        ]

        for input_str, expected_priority in test_cases:
            result = extractor._parse_priority(input_str)
            assert result == expected_priority

    def test_extract_llm_failure(self, sample_document, mock_llm_provider):
        """Test extraction when LLM fails."""
        # Make LLM fail
        mock_llm_provider.generate_structured.side_effect = LLMProviderError(
            "LLM failed"
        )

        extractor = RequirementsExtractor(mock_llm_provider)
        extracted = extractor.extract([sample_document])

        # Should return fallback extraction
        assert isinstance(extracted, ExtractedRequirements)
        assert "incomplete" in extracted.summary.lower()
        assert extracted.domain == "Unknown (extraction failed)"
        assert extracted.total_requirements == 0

    def test_create_fallback_extraction(self, sample_document):
        """Test creating fallback extraction."""
        extractor = RequirementsExtractor(Mock())

        extracted = extractor._create_fallback_extraction(
            [sample_document], error="Test error"
        )

        assert isinstance(extracted, ExtractedRequirements)
        assert "incomplete" in extracted.summary
        assert "Test error" in extracted.summary
        assert len(extracted.documents) == 1
        assert extracted.total_requirements == 0

    def test_get_response_schema(self):
        """Test LLM response schema structure."""
        extractor = RequirementsExtractor(Mock())

        schema = extractor._get_response_schema()

        assert schema["type"] == "object"
        assert "summary" in schema["properties"]
        assert "domain" in schema["properties"]
        assert "requirements" in schema["properties"]
        assert "stakeholders" in schema["properties"]
        assert "objectives" in schema["properties"]

        # Check required fields
        assert "summary" in schema["required"]
        assert "domain" in schema["required"]
        assert "requirements" in schema["required"]

    def test_parse_result_stakeholder_linking(self, sample_document):
        """Test that stakeholders are linked to requirements."""
        extractor = RequirementsExtractor(Mock())

        result = {
            "summary": "Test",
            "domain": "test",
            "requirements": [
                {
                    "id": "REQ-001",
                    "text": "Requirement 1",
                    "type": "functional",
                    "priority": "high",
                    "stakeholders": ["Alice"],
                },
                {
                    "id": "REQ-002",
                    "text": "Requirement 2",
                    "type": "functional",
                    "priority": "medium",
                    "stakeholders": ["Alice", "Bob"],
                },
            ],
            "stakeholders": [
                {
                    "name": "Alice",
                    "role": "PM",
                    "organization": "Product",
                    "interests": ["Features"],
                },
                {
                    "name": "Bob",
                    "role": "Engineer",
                    "organization": "Engineering",
                    "interests": ["Performance"],
                },
            ],
            "objectives": [],
            "constraints": [],
            "assumptions": [],
            "risks": [],
        }

        extracted = extractor._parse_result(result, [sample_document])

        # Check stakeholder linking
        alice = next(s for s in extracted.stakeholders if s.name == "Alice")
        bob = next(s for s in extracted.stakeholders if s.name == "Bob")

        assert "REQ-001" in alice.requirements
        assert "REQ-002" in alice.requirements
        assert "REQ-002" in bob.requirements
        assert "REQ-001" not in bob.requirements


class TestExtractedRequirementsIntegration:
    """Integration tests for full extraction workflow."""

    def test_full_extraction_workflow(self, sample_document, mock_llm_provider):
        """Test complete extraction workflow."""
        # Create extractor
        extractor = RequirementsExtractor(mock_llm_provider)

        # Extract
        extracted = extractor.extract([sample_document])

        # Verify structure
        assert extracted.domain is not None
        assert extracted.summary != ""
        assert len(extracted.requirements) > 0

        # Verify requirement properties
        for req in extracted.requirements:
            assert req.id != ""
            assert req.text != ""
            assert isinstance(req.requirement_type, RequirementType)
            assert isinstance(req.priority, Priority)

        # Verify stakeholder properties
        for sh in extracted.stakeholders:
            assert sh.name != ""

        # Verify can convert to summary dict
        summary_dict = extracted.to_summary_dict()
        assert "domain" in summary_dict
        assert "total_requirements" in summary_dict
        assert "stakeholders" in summary_dict

    def test_extraction_with_constraints_and_risks(
        self, sample_document, mock_llm_provider
    ):
        """Test extraction includes constraints and risks."""
        extractor = RequirementsExtractor(mock_llm_provider)
        extracted = extractor.extract([sample_document])

        assert len(extracted.constraints) > 0
        assert len(extracted.risks) > 0

        # Verify in summary dict
        summary = extracted.to_summary_dict()
        assert "constraints" in summary
        assert "risks" in summary
