"""
Test fixtures for document processing tests.

Provides mock data and objects for testing document parsing and extraction.
"""

import pytest
from unittest.mock import Mock

from graph_analytics_ai.ai.documents.models import (
    Document,
    DocumentMetadata,
    TextChunk,
    ExtractedRequirements,
    Requirement,
    RequirementType,
    Stakeholder,
    Objective,
    Priority,
)


@pytest.fixture
def sample_text_content():
    """Sample text content for testing."""
    return """Business Requirements Document
    
Project: E-commerce Platform Modernization

Executive Summary:
We need to modernize our e-commerce platform to improve performance,
scalability, and user experience. The current system cannot handle
peak loads during sales events.

Stakeholders:
- Jane Smith, VP of Engineering
- Bob Johnson, Product Manager
- Sarah Lee, Head of Operations

Requirements:

REQ-001: The system must handle 10,000 concurrent users
Priority: Critical
Type: Non-Functional

REQ-002: Shopping cart must persist across sessions
Priority: High
Type: Functional

REQ-003: Implement real-time inventory tracking
Priority: High
Type: Functional

Constraints:
- Budget limit of $500,000
- Must be completed by Q2 2025
- Must maintain backward compatibility with existing API

Risks:
- Database migration may cause downtime
- Third-party payment integration complexity
"""


@pytest.fixture
def temp_text_file(sample_text_content, tmp_path):
    """Create a temporary text file."""
    file_path = tmp_path / "requirements.txt"
    file_path.write_text(sample_text_content)
    return str(file_path)


@pytest.fixture
def temp_markdown_file(tmp_path):
    """Create a temporary markdown file."""
    content = """# Business Requirements

## Overview
This is a test document.

## Requirements
- REQ-001: First requirement
- REQ-002: Second requirement
"""
    file_path = tmp_path / "requirements.md"
    file_path.write_text(content)
    return str(file_path)


@pytest.fixture
def sample_document_metadata(temp_text_file):
    """Sample document metadata."""
    return DocumentMetadata.from_file(temp_text_file)


@pytest.fixture
def sample_document(sample_document_metadata, sample_text_content):
    """Sample document object."""
    return Document(metadata=sample_document_metadata, content=sample_text_content)


@pytest.fixture
def sample_chunked_document(sample_document):
    """Sample document with chunks."""
    doc = sample_document
    doc.chunks = [
        TextChunk(content=doc.content[:500], chunk_index=0, start_char=0, end_char=500),
        TextChunk(
            content=doc.content[400:900],  # Overlapping
            chunk_index=1,
            start_char=400,
            end_char=900,
        ),
    ]
    return doc


@pytest.fixture
def sample_requirements():
    """Sample extracted requirements."""
    return [
        Requirement(
            id="REQ-001",
            text="The system must handle 10,000 concurrent users",
            requirement_type=RequirementType.NON_FUNCTIONAL,
            priority=Priority.CRITICAL,
            stakeholders=["Jane Smith"],
        ),
        Requirement(
            id="REQ-002",
            text="Shopping cart must persist across sessions",
            requirement_type=RequirementType.FUNCTIONAL,
            priority=Priority.HIGH,
            stakeholders=["Bob Johnson"],
        ),
        Requirement(
            id="REQ-003",
            text="Implement real-time inventory tracking",
            requirement_type=RequirementType.FUNCTIONAL,
            priority=Priority.HIGH,
            stakeholders=["Sarah Lee", "Bob Johnson"],
        ),
    ]


@pytest.fixture
def sample_stakeholders():
    """Sample stakeholders."""
    return [
        Stakeholder(
            name="Jane Smith",
            role="VP of Engineering",
            organization="Engineering",
            interests=["Performance", "Scalability"],
            requirements=["REQ-001"],
        ),
        Stakeholder(
            name="Bob Johnson",
            role="Product Manager",
            organization="Product",
            interests=["User Experience", "Features"],
            requirements=["REQ-002", "REQ-003"],
        ),
        Stakeholder(
            name="Sarah Lee",
            role="Head of Operations",
            organization="Operations",
            interests=["Reliability", "Inventory Management"],
            requirements=["REQ-003"],
        ),
    ]


@pytest.fixture
def sample_objectives():
    """Sample objectives."""
    return [
        Objective(
            id="OBJ-001",
            title="Improve Platform Performance",
            description="Modernize platform to handle peak loads",
            priority=Priority.CRITICAL,
            success_criteria=[
                "Handle 10,000 concurrent users",
                "99.9% uptime during sales events",
            ],
            related_requirements=["REQ-001"],
            stakeholders=["Jane Smith"],
        ),
        Objective(
            id="OBJ-002",
            title="Enhance User Experience",
            description="Improve shopping cart and checkout flow",
            priority=Priority.HIGH,
            success_criteria=[
                "Cart persistence across sessions",
                "Real-time inventory updates",
            ],
            related_requirements=["REQ-002", "REQ-003"],
            stakeholders=["Bob Johnson", "Sarah Lee"],
        ),
    ]


@pytest.fixture
def sample_extracted_requirements(
    sample_document, sample_requirements, sample_stakeholders, sample_objectives
):
    """Sample complete extracted requirements."""
    return ExtractedRequirements(
        documents=[sample_document],
        requirements=sample_requirements,
        stakeholders=sample_stakeholders,
        objectives=sample_objectives,
        summary="E-commerce platform modernization project to improve performance and scalability.",
        domain="e-commerce",
        constraints=[
            "Budget limit of $500,000",
            "Must be completed by Q2 2025",
            "Backward compatibility required",
        ],
        assumptions=["Existing API will be maintained", "Current user base will grow"],
        risks=["Database migration downtime", "Payment integration complexity"],
    )


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing."""
    provider = Mock()

    # Mock generate_structured to return valid requirements extraction
    provider.generate_structured.return_value = {
        "summary": "E-commerce platform modernization project.",
        "domain": "e-commerce",
        "requirements": [
            {
                "id": "REQ-001",
                "text": "The system must handle 10,000 concurrent users",
                "type": "non_functional",
                "priority": "critical",
                "stakeholders": ["Jane Smith"],
            },
            {
                "id": "REQ-002",
                "text": "Shopping cart must persist",
                "type": "functional",
                "priority": "high",
                "stakeholders": ["Bob Johnson"],
            },
        ],
        "stakeholders": [
            {
                "name": "Jane Smith",
                "role": "VP of Engineering",
                "organization": "Engineering",
                "interests": ["Performance"],
            },
            {
                "name": "Bob Johnson",
                "role": "Product Manager",
                "organization": "Product",
                "interests": ["UX"],
            },
        ],
        "objectives": [
            {
                "id": "OBJ-001",
                "title": "Improve Performance",
                "description": "Handle peak loads",
                "priority": "critical",
                "success_criteria": ["10K concurrent users"],
                "related_requirements": ["REQ-001"],
            }
        ],
        "constraints": ["Budget $500K", "Q2 2025 deadline"],
        "assumptions": ["User growth"],
        "risks": ["Migration downtime"],
    }

    return provider
