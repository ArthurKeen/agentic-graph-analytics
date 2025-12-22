"""
Data models for document processing.

These models represent business requirement documents, extracted requirements,
stakeholders, and objectives.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
from pathlib import Path


class DocumentType(Enum):
    """Type of document."""

    TEXT = "text"
    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "markdown"
    HTML = "html"
    UNKNOWN = "unknown"


class RequirementType(Enum):
    """Type of business requirement."""

    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    BUSINESS = "business"
    TECHNICAL = "technical"
    CONSTRAINT = "constraint"
    OBJECTIVE = "objective"


class Priority(Enum):
    """Priority level."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class DocumentMetadata:
    """Metadata about a source document."""

    file_path: str
    """Path to the document file."""

    file_name: str
    """Name of the document file."""

    document_type: DocumentType
    """Type of document."""

    file_size: int = 0
    """File size in bytes."""

    created_at: Optional[datetime] = None
    """When the document was created."""

    modified_at: Optional[datetime] = None
    """When the document was last modified."""

    author: Optional[str] = None
    """Document author (if available)."""

    title: Optional[str] = None
    """Document title (if available)."""

    @classmethod
    def from_file(cls, file_path: str) -> "DocumentMetadata":
        """
        Create metadata from a file path.

        Args:
            file_path: Path to the document file.

        Returns:
            DocumentMetadata instance.
        """
        path = Path(file_path)

        # Determine document type from extension
        ext = path.suffix.lower()
        doc_type_map = {
            ".txt": DocumentType.TEXT,
            ".md": DocumentType.MARKDOWN,
            ".pdf": DocumentType.PDF,
            ".docx": DocumentType.DOCX,
            ".html": DocumentType.HTML,
            ".htm": DocumentType.HTML,
        }
        doc_type = doc_type_map.get(ext, DocumentType.UNKNOWN)

        # Get file stats
        file_size = 0
        created_at = None
        modified_at = None

        if path.exists():
            stats = path.stat()
            file_size = stats.st_size
            created_at = datetime.fromtimestamp(stats.st_ctime)
            modified_at = datetime.fromtimestamp(stats.st_mtime)

        return cls(
            file_path=str(path),
            file_name=path.name,
            document_type=doc_type,
            file_size=file_size,
            created_at=created_at,
            modified_at=modified_at,
        )


@dataclass
class TextChunk:
    """A chunk of text extracted from a document."""

    content: str
    """The text content."""

    chunk_index: int = 0
    """Index of this chunk in the document."""

    start_char: int = 0
    """Starting character position in original document."""

    end_char: int = 0
    """Ending character position in original document."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata about this chunk."""

    @property
    def length(self) -> int:
        """Length of the chunk content."""
        return len(self.content)

    @property
    def word_count(self) -> int:
        """Approximate word count."""
        return len(self.content.split())


@dataclass
class Document:
    """A processed document with extracted content."""

    metadata: DocumentMetadata
    """Document metadata."""

    content: str
    """Full extracted text content."""

    chunks: List[TextChunk] = field(default_factory=list)
    """Document split into chunks (if chunked)."""

    language: str = "en"
    """Detected or specified language."""

    encoding: str = "utf-8"
    """Text encoding."""

    extraction_errors: List[str] = field(default_factory=list)
    """Any errors encountered during extraction."""

    @property
    def length(self) -> int:
        """Length of document content."""
        return len(self.content)

    @property
    def word_count(self) -> int:
        """Approximate word count."""
        return len(self.content.split())

    @property
    def is_chunked(self) -> bool:
        """Whether document has been split into chunks."""
        return len(self.chunks) > 0

    def get_preview(self, max_chars: int = 200) -> str:
        """
        Get preview of document content.

        Args:
            max_chars: Maximum characters in preview.

        Returns:
            Preview string.
        """
        if len(self.content) <= max_chars:
            return self.content
        return self.content[:max_chars] + "..."


@dataclass
class Requirement:
    """A single business requirement extracted from documents."""

    id: str
    """Unique identifier for this requirement."""

    text: str
    """The requirement text."""

    requirement_type: RequirementType
    """Type of requirement."""

    priority: Priority = Priority.UNKNOWN
    """Priority level."""

    source_document: Optional[str] = None
    """Source document filename."""

    stakeholders: List[str] = field(default_factory=list)
    """Stakeholders associated with this requirement."""

    dependencies: List[str] = field(default_factory=list)
    """IDs of dependent requirements."""

    tags: List[str] = field(default_factory=list)
    """Tags or categories."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""

    @property
    def is_critical(self) -> bool:
        """Whether this is a critical requirement."""
        return self.priority == Priority.CRITICAL

    @property
    def is_high_priority(self) -> bool:
        """Whether this is high or critical priority."""
        return self.priority in (Priority.CRITICAL, Priority.HIGH)


@dataclass
class Stakeholder:
    """A stakeholder identified in the requirements."""

    name: str
    """Stakeholder name."""

    role: Optional[str] = None
    """Role or title."""

    organization: Optional[str] = None
    """Organization or department."""

    interests: List[str] = field(default_factory=list)
    """Key interests or concerns."""

    requirements: List[str] = field(default_factory=list)
    """IDs of requirements they're associated with."""

    contact: Optional[str] = None
    """Contact information (if available)."""


@dataclass
class Objective:
    """A business objective extracted from documents."""

    id: str
    """Unique identifier."""

    title: str
    """Objective title."""

    description: str
    """Detailed description."""

    priority: Priority = Priority.UNKNOWN
    """Priority level."""

    success_criteria: List[str] = field(default_factory=list)
    """Measurable success criteria."""

    related_requirements: List[str] = field(default_factory=list)
    """IDs of related requirements."""

    stakeholders: List[str] = field(default_factory=list)
    """Stakeholder names."""

    timeline: Optional[str] = None
    """Expected timeline (if specified)."""

    metrics: List[str] = field(default_factory=list)
    """Key metrics or KPIs."""


@dataclass
class ExtractedRequirements:
    """
    Complete set of requirements extracted from documents.

    This is the main output of the document processing phase.
    """

    documents: List[Document]
    """Source documents."""

    requirements: List[Requirement] = field(default_factory=list)
    """All extracted requirements."""

    stakeholders: List[Stakeholder] = field(default_factory=list)
    """Identified stakeholders."""

    objectives: List[Objective] = field(default_factory=list)
    """Business objectives."""

    summary: str = ""
    """Executive summary of requirements."""

    domain: Optional[str] = None
    """Identified business domain."""

    constraints: List[str] = field(default_factory=list)
    """Identified constraints (budget, time, technical, etc.)."""

    assumptions: List[str] = field(default_factory=list)
    """Identified assumptions."""

    risks: List[str] = field(default_factory=list)
    """Identified risks."""

    @property
    def total_requirements(self) -> int:
        """Total number of requirements."""
        return len(self.requirements)

    @property
    def critical_requirements(self) -> List[Requirement]:
        """Get all critical requirements."""
        return [r for r in self.requirements if r.is_critical]

    @property
    def high_priority_requirements(self) -> List[Requirement]:
        """Get all high/critical priority requirements."""
        return [r for r in self.requirements if r.is_high_priority]

    def get_requirements_by_type(self, req_type: RequirementType) -> List[Requirement]:
        """Get requirements of a specific type."""
        return [r for r in self.requirements if r.requirement_type == req_type]

    def get_requirements_by_stakeholder(
        self, stakeholder_name: str
    ) -> List[Requirement]:
        """Get requirements associated with a stakeholder."""
        return [r for r in self.requirements if stakeholder_name in r.stakeholders]

    def to_summary_dict(self) -> Dict[str, Any]:
        """
        Convert to summary dictionary for LLM consumption.

        Returns:
            Dictionary suitable for JSON serialization.
        """
        return {
            "summary": self.summary,
            "domain": self.domain,
            "total_documents": len(self.documents),
            "total_requirements": self.total_requirements,
            "requirements_by_type": {
                req_type.value: len(self.get_requirements_by_type(req_type))
                for req_type in RequirementType
            },
            "stakeholders": [
                {
                    "name": s.name,
                    "role": s.role,
                    "num_requirements": len(s.requirements),
                }
                for s in self.stakeholders
            ],
            "objectives": [
                {
                    "title": o.title,
                    "priority": o.priority.value,
                    "success_criteria_count": len(o.success_criteria),
                }
                for o in self.objectives
            ],
            "constraints": self.constraints,
            "risks": self.risks[:5],  # Top 5 risks
            "critical_requirements_count": len(self.critical_requirements),
        }
