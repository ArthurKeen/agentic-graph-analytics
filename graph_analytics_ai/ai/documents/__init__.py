"""
Document processing and requirements extraction module.

This module provides tools for parsing business requirement documents
and extracting structured requirements using LLMs.

Supported formats:
- Plain text (.txt)
- Markdown (.md)
- PDF (.pdf) - requires pdfplumber or PyPDF2
- DOCX (.docx) - requires python-docx
- HTML (.html) - requires beautifulsoup4

Example:
    >>> from graph_analytics_ai.ai.documents import (
    ...     parse_documents,
    ...     RequirementsExtractor
    ... )
    >>> from graph_analytics_ai.ai.llm import create_llm_provider
    >>>
    >>> # Parse documents
    >>> docs = parse_documents([
    ...     "requirements.pdf",
    ...     "scope.docx",
    ...     "business_case.md"
    ... ])
    >>>
    >>> print(f"Parsed {len(docs)} documents")
    >>> for doc in docs:
    ...     print(f"- {doc.metadata.file_name}: {doc.word_count} words")
    >>>
    >>> # Extract requirements with LLM
    >>> provider = create_llm_provider()
    >>> extractor = RequirementsExtractor(provider)
    >>> extracted = extractor.extract(docs)
    >>>
    >>> print(f"\nDomain: {extracted.domain}")
    >>> print(f"Total requirements: {extracted.total_requirements}")
    >>> print(f"Critical requirements: {len(extracted.critical_requirements)}")
    >>> print(f"Stakeholders: {len(extracted.stakeholders)}")
    >>> print(f"Objectives: {len(extracted.objectives)}")
    >>>
    >>> print(f"\nSummary:\n{extracted.summary}")
    >>>
    >>> # Show critical requirements
    >>> print("\nCritical Requirements:")
    >>> for req in extracted.critical_requirements:
    ...     print(f"- {req.id}: {req.text}")
"""

from .models import (
    Document,
    DocumentMetadata,
    DocumentType,
    TextChunk,
    Requirement,
    RequirementType,
    Stakeholder,
    Objective,
    Priority,
    ExtractedRequirements,
)

from .parser import (
    DocumentParser,
    ParserError,
    UnsupportedFormatError,
    parse_document,
    parse_documents,
)

from .extractor import RequirementsExtractor


__all__ = [
    # Models
    "Document",
    "DocumentMetadata",
    "DocumentType",
    "TextChunk",
    "Requirement",
    "RequirementType",
    "Stakeholder",
    "Objective",
    "Priority",
    "ExtractedRequirements",
    # Parser
    "DocumentParser",
    "ParserError",
    "UnsupportedFormatError",
    "parse_document",
    "parse_documents",
    # Extractor
    "RequirementsExtractor",
]
