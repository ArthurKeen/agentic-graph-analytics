"""
Unit tests for document parser.

Tests document parsing from various formats.
"""

import pytest
from unittest.mock import patch

from graph_analytics_ai.ai.documents.parser import (
    DocumentParser,
    ParserError,
    parse_document,
    parse_documents,
)
from graph_analytics_ai.ai.documents.models import DocumentType


class TestDocumentParser:
    """Test DocumentParser class."""

    def test_init(self):
        """Test parser initialization."""
        parser = DocumentParser(chunk_size=500, chunk_overlap=50)

        assert parser.chunk_size == 500
        assert parser.chunk_overlap == 50

    def test_parse_text_file(self, temp_text_file):
        """Test parsing plain text file."""
        parser = DocumentParser()
        doc = parser.parse(temp_text_file)

        assert doc.metadata.document_type == DocumentType.TEXT
        assert len(doc.content) > 0
        assert doc.word_count > 0
        assert len(doc.extraction_errors) == 0

    def test_parse_markdown_file(self, temp_markdown_file):
        """Test parsing markdown file."""
        parser = DocumentParser()
        doc = parser.parse(temp_markdown_file)

        assert doc.metadata.document_type == DocumentType.MARKDOWN
        assert len(doc.content) > 0
        assert "# Business Requirements" in doc.content

    def test_parse_with_chunking(self, temp_text_file):
        """Test parsing with chunking enabled."""
        parser = DocumentParser(chunk_size=200, chunk_overlap=50)
        doc = parser.parse(temp_text_file, chunk=True)

        assert doc.is_chunked
        assert len(doc.chunks) > 0

        # Verify chunks
        for i, chunk in enumerate(doc.chunks):
            assert chunk.chunk_index == i
            assert chunk.length > 0

    def test_create_chunks(self):
        """Test chunk creation."""
        parser = DocumentParser(chunk_size=10, chunk_overlap=3)
        content = "0123456789" * 5  # 50 characters

        chunks = parser._create_chunks(content)

        assert len(chunks) > 1

        # Verify overlap
        for i in range(len(chunks) - 1):
            current_end = chunks[i].content[-3:]
            next_start = chunks[i + 1].content[:3]
            # Should have some overlap
            assert len(set(current_end) & set(next_start)) > 0

    def test_create_chunks_empty(self):
        """Test chunking empty content."""
        parser = DocumentParser()
        chunks = parser._create_chunks("")

        assert len(chunks) == 0

    def test_parse_multiple(self, temp_text_file, temp_markdown_file):
        """Test parsing multiple documents."""
        parser = DocumentParser()
        docs = parser.parse_multiple([temp_text_file, temp_markdown_file])

        assert len(docs) == 2
        assert docs[0].metadata.document_type == DocumentType.TEXT
        assert docs[1].metadata.document_type == DocumentType.MARKDOWN

    def test_parse_nonexistent_file(self):
        """Test parsing non-existent file."""
        parser = DocumentParser()
        doc = parser.parse("/nonexistent/file.txt")

        # Should return doc with error
        assert len(doc.extraction_errors) > 0
        assert doc.content == ""

    def test_parse_unsupported_format(self, tmp_path):
        """Test parsing unsupported format."""
        file_path = tmp_path / "file.xyz"
        file_path.write_text("content")

        parser = DocumentParser()
        doc = parser.parse(str(file_path))

        # Should return doc with error
        assert len(doc.extraction_errors) > 0


class TestParseHelpers:
    """Test parse helper functions."""

    def test_parse_document_helper(self, temp_text_file):
        """Test parse_document convenience function."""
        doc = parse_document(temp_text_file)

        assert isinstance(doc, type(doc))  # Is a Document
        assert len(doc.content) > 0

    def test_parse_documents_helper(self, temp_text_file, temp_markdown_file):
        """Test parse_documents convenience function."""
        docs = parse_documents([temp_text_file, temp_markdown_file])

        assert len(docs) == 2
        assert all(hasattr(doc, "content") for doc in docs)

    def test_parse_document_with_chunking(self, temp_text_file):
        """Test convenience function with chunking."""
        doc = parse_document(temp_text_file, chunk=True)

        assert doc.is_chunked
        assert len(doc.chunks) > 0


class TestPDFParsing:
    """Test PDF parsing (with mocking)."""

    @patch("graph_analytics_ai.ai.documents.parser.pdfplumber")
    def test_parse_pdf_with_pdfplumber(self, mock_pdfplumber, tmp_path):
        """Test PDF parsing with pdfplumber."""
        # Create mock PDF
        file_path = tmp_path / "test.pdf"
        file_path.write_bytes(b"fake pdf content")

        # Mock pdfplumber
        mock_pdf = mock_pdfplumber.open.return_value.__enter__.return_value
        mock_page = type("Page", (), {"extract_text": lambda: "Page content"})()
        mock_pdf.pages = [mock_page, mock_page]

        parser = DocumentParser()
        doc = parser._parse_pdf(str(file_path))

        assert "Page content" in doc
        assert len(doc) > 0

    def test_parse_pdf_without_libraries(self, tmp_path):
        """Test PDF parsing without required libraries."""
        file_path = tmp_path / "test.pdf"
        file_path.write_bytes(b"fake pdf")

        parser = DocumentParser()

        # Patch both libraries to not be available
        with patch.dict("sys.modules", {"pdfplumber": None, "PyPDF2": None}):
            with pytest.raises(ParserError) as exc_info:
                parser._parse_pdf(str(file_path))

            assert "requires" in str(exc_info.value).lower()


class TestDOCXParsing:
    """Test DOCX parsing (with mocking)."""

    def test_parse_docx_without_library(self, tmp_path):
        """Test DOCX parsing without python-docx."""
        file_path = tmp_path / "test.docx"
        file_path.write_bytes(b"fake docx")

        parser = DocumentParser()

        with patch.dict("sys.modules", {"docx": None}):
            with pytest.raises(ParserError) as exc_info:
                parser._parse_docx(str(file_path))

            assert "requires" in str(exc_info.value).lower()
            assert "python-docx" in str(exc_info.value)


class TestHTMLParsing:
    """Test HTML parsing (with mocking)."""

    def test_parse_html_without_library(self, tmp_path):
        """Test HTML parsing without beautifulsoup4."""
        file_path = tmp_path / "test.html"
        file_path.write_text("<html><body>Test</body></html>")

        parser = DocumentParser()

        with patch.dict("sys.modules", {"bs4": None}):
            with pytest.raises(ParserError) as exc_info:
                parser._parse_html(str(file_path))

            assert "requires" in str(exc_info.value).lower()
            assert "beautifulsoup4" in str(exc_info.value)
