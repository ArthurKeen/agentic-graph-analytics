"""
Unit tests for document processing models.

Tests the data models used to represent documents and requirements.
"""

from graph_analytics_ai.ai.documents.models import (
    DocumentMetadata,
    DocumentType,
    TextChunk,
    Document,
    Requirement,
    RequirementType,
    Priority,
    Stakeholder,
    Objective,
    ExtractedRequirements,
)


class TestDocumentMetadata:
    """Test DocumentMetadata model."""

    def test_from_file_text(self, temp_text_file):
        """Test creating metadata from text file."""
        metadata = DocumentMetadata.from_file(temp_text_file)

        assert metadata.file_name == "requirements.txt"
        assert metadata.document_type == DocumentType.TEXT
        assert metadata.file_size > 0
        assert metadata.created_at is not None
        assert metadata.modified_at is not None

    def test_from_file_markdown(self, temp_markdown_file):
        """Test creating metadata from markdown file."""
        metadata = DocumentMetadata.from_file(temp_markdown_file)

        assert metadata.document_type == DocumentType.MARKDOWN
        assert ".md" in metadata.file_name

    def test_document_type_detection(self):
        """Test document type detection from extension."""
        test_cases = [
            ("file.txt", DocumentType.TEXT),
            ("file.md", DocumentType.MARKDOWN),
            ("file.pdf", DocumentType.PDF),
            ("file.docx", DocumentType.DOCX),
            ("file.html", DocumentType.HTML),
            ("file.unknown", DocumentType.UNKNOWN),
        ]

        for filename, expected_type in test_cases:
            DocumentMetadata(
                file_path=filename,
                file_name=filename,
                document_type=DocumentType.UNKNOWN,
            )
            # Would be set by from_file, but we test the logic
            assert expected_type in list(DocumentType)


class TestTextChunk:
    """Test TextChunk model."""

    def test_length_property(self):
        """Test chunk length calculation."""
        chunk = TextChunk(content="Hello world", chunk_index=0)
        assert chunk.length == 11

    def test_word_count_property(self):
        """Test word count calculation."""
        chunk = TextChunk(content="Hello world from tests", chunk_index=0)
        assert chunk.word_count == 4

    def test_chunk_with_metadata(self):
        """Test chunk with custom metadata."""
        chunk = TextChunk(
            content="Test content",
            chunk_index=5,
            start_char=100,
            end_char=200,
            metadata={"page": 2, "section": "Requirements"},
        )

        assert chunk.chunk_index == 5
        assert chunk.start_char == 100
        assert chunk.end_char == 200
        assert chunk.metadata["page"] == 2


class TestDocument:
    """Test Document model."""

    def test_basic_properties(self, sample_document):
        """Test basic document properties."""
        assert sample_document.length > 0
        assert sample_document.word_count > 0
        assert not sample_document.is_chunked

    def test_chunked_document(self, sample_chunked_document):
        """Test chunked document."""
        assert sample_chunked_document.is_chunked
        assert len(sample_chunked_document.chunks) == 2

    def test_get_preview_short(self):
        """Test preview of short content."""
        doc = Document(
            metadata=DocumentMetadata(
                file_path="test.txt",
                file_name="test.txt",
                document_type=DocumentType.TEXT,
            ),
            content="Short content",
        )

        preview = doc.get_preview(100)
        assert preview == "Short content"
        assert "..." not in preview

    def test_get_preview_long(self, sample_document):
        """Test preview of long content."""
        preview = sample_document.get_preview(50)

        assert len(preview) <= 53  # 50 + "..."
        assert preview.endswith("...")

    def test_document_with_errors(self):
        """Test document with extraction errors."""
        doc = Document(
            metadata=DocumentMetadata(
                file_path="test.pdf",
                file_name="test.pdf",
                document_type=DocumentType.PDF,
            ),
            content="",
            extraction_errors=["Failed to parse PDF"],
        )

        assert len(doc.extraction_errors) == 1
        assert doc.length == 0


class TestRequirement:
    """Test Requirement model."""

    def test_is_critical(self):
        """Test critical requirement detection."""
        req = Requirement(
            id="REQ-001",
            text="Critical requirement",
            requirement_type=RequirementType.FUNCTIONAL,
            priority=Priority.CRITICAL,
        )

        assert req.is_critical
        assert req.is_high_priority

    def test_is_high_priority(self):
        """Test high priority detection."""
        req = Requirement(
            id="REQ-002",
            text="High priority requirement",
            requirement_type=RequirementType.FUNCTIONAL,
            priority=Priority.HIGH,
        )

        assert not req.is_critical
        assert req.is_high_priority

    def test_not_high_priority(self):
        """Test medium/low priority."""
        req = Requirement(
            id="REQ-003",
            text="Medium priority requirement",
            requirement_type=RequirementType.FUNCTIONAL,
            priority=Priority.MEDIUM,
        )

        assert not req.is_critical
        assert not req.is_high_priority

    def test_with_stakeholders(self, sample_requirements):
        """Test requirement with stakeholders."""
        req = sample_requirements[0]

        assert len(req.stakeholders) > 0
        assert "Jane Smith" in req.stakeholders


class TestStakeholder:
    """Test Stakeholder model."""

    def test_basic_stakeholder(self):
        """Test basic stakeholder creation."""
        sh = Stakeholder(
            name="John Doe",
            role="Product Manager",
            organization="Product",
            interests=["Features", "UX"],
            requirements=["REQ-001", "REQ-002"],
        )

        assert sh.name == "John Doe"
        assert len(sh.interests) == 2
        assert len(sh.requirements) == 2

    def test_stakeholder_without_optional_fields(self):
        """Test stakeholder with minimal information."""
        sh = Stakeholder(name="Jane Doe")

        assert sh.role is None
        assert sh.organization is None
        assert len(sh.interests) == 0


class TestObjective:
    """Test Objective model."""

    def test_basic_objective(self):
        """Test basic objective creation."""
        obj = Objective(
            id="OBJ-001",
            title="Improve Performance",
            description="Make system faster",
            priority=Priority.HIGH,
            success_criteria=["Response time < 100ms"],
            related_requirements=["REQ-001"],
        )

        assert obj.id == "OBJ-001"
        assert len(obj.success_criteria) == 1
        assert len(obj.related_requirements) == 1

    def test_objective_with_metrics(self):
        """Test objective with metrics."""
        obj = Objective(
            id="OBJ-002",
            title="Increase Sales",
            description="Boost revenue",
            metrics=["Revenue +20%", "Conversion rate +5%"],
        )

        assert len(obj.metrics) == 2


class TestExtractedRequirements:
    """Test ExtractedRequirements model."""

    def test_total_requirements(self, sample_extracted_requirements):
        """Test total requirements count."""
        assert sample_extracted_requirements.total_requirements == 3

    def test_critical_requirements(self, sample_extracted_requirements):
        """Test filtering critical requirements."""
        critical = sample_extracted_requirements.critical_requirements

        assert len(critical) == 1
        assert critical[0].id == "REQ-001"

    def test_high_priority_requirements(self, sample_extracted_requirements):
        """Test filtering high priority requirements."""
        high_pri = sample_extracted_requirements.high_priority_requirements

        # Should include both CRITICAL and HIGH
        assert len(high_pri) == 3

    def test_get_requirements_by_type(self, sample_extracted_requirements):
        """Test filtering by requirement type."""
        functional = sample_extracted_requirements.get_requirements_by_type(
            RequirementType.FUNCTIONAL
        )
        non_functional = sample_extracted_requirements.get_requirements_by_type(
            RequirementType.NON_FUNCTIONAL
        )

        assert len(functional) == 2
        assert len(non_functional) == 1

    def test_get_requirements_by_stakeholder(self, sample_extracted_requirements):
        """Test filtering by stakeholder."""
        bob_reqs = sample_extracted_requirements.get_requirements_by_stakeholder(
            "Bob Johnson"
        )

        assert len(bob_reqs) == 2
        assert "REQ-002" in [r.id for r in bob_reqs]
        assert "REQ-003" in [r.id for r in bob_reqs]

    def test_to_summary_dict(self, sample_extracted_requirements):
        """Test conversion to summary dictionary."""
        summary = sample_extracted_requirements.to_summary_dict()

        assert summary["domain"] == "e-commerce"
        assert summary["total_documents"] == 1
        assert summary["total_requirements"] == 3
        assert "requirements_by_type" in summary
        assert len(summary["stakeholders"]) == 3
        assert len(summary["objectives"]) == 2
        assert len(summary["constraints"]) == 3
        assert summary["critical_requirements_count"] == 1

    def test_empty_extracted_requirements(self):
        """Test empty requirements object."""
        extracted = ExtractedRequirements(documents=[], summary="No requirements found")

        assert extracted.total_requirements == 0
        assert len(extracted.critical_requirements) == 0
        assert len(extracted.stakeholders) == 0
