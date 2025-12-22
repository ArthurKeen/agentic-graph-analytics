"""
Models for analysis report generation.

Defines data structures for reports, insights, and recommendations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any


class ReportFormat(Enum):
    """Output format for reports."""

    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    TEXT = "text"


class InsightType(Enum):
    """Type of insight."""

    KEY_FINDING = "key_finding"
    PATTERN = "pattern"
    ANOMALY = "anomaly"
    TREND = "trend"
    CORRELATION = "correlation"


class RecommendationType(Enum):
    """Type of recommendation."""

    ACTION = "action"
    OPTIMIZATION = "optimization"
    INVESTIGATION = "investigation"
    MONITORING = "monitoring"


@dataclass
class Insight:
    """
    A single insight from analysis.

    Represents a key finding, pattern, or observation.
    """

    title: str
    """Short title of the insight."""

    description: str
    """Detailed description."""

    insight_type: InsightType
    """Type of insight."""

    confidence: float = 1.0
    """Confidence level (0-1)."""

    supporting_data: Dict[str, Any] = field(default_factory=dict)
    """Data supporting this insight."""

    business_impact: str = ""
    """Business impact description."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "insight_type": self.insight_type.value,
            "confidence": self.confidence,
            "supporting_data": self.supporting_data,
            "business_impact": self.business_impact,
        }


@dataclass
class Recommendation:
    """
    Actionable recommendation based on analysis.
    """

    title: str
    """Short title of recommendation."""

    description: str
    """Detailed description of what to do."""

    recommendation_type: RecommendationType
    """Type of recommendation."""

    priority: str = "medium"
    """Priority: low, medium, high, critical."""

    effort: str = "medium"
    """Estimated effort: low, medium, high."""

    expected_impact: str = ""
    """Expected business impact."""

    related_insights: List[str] = field(default_factory=list)
    """Titles of related insights."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "recommendation_type": self.recommendation_type.value,
            "priority": self.priority,
            "effort": self.effort,
            "expected_impact": self.expected_impact,
            "related_insights": self.related_insights,
        }


@dataclass
class ReportSection:
    """
    A section of the report.
    """

    title: str
    """Section title."""

    content: str
    """Section content (markdown format)."""

    subsections: List["ReportSection"] = field(default_factory=list)
    """Nested subsections."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "content": self.content,
            "subsections": [s.to_dict() for s in self.subsections],
            "metadata": self.metadata,
        }


@dataclass
class AnalysisReport:
    """
    Complete analysis report.

    Contains insights, recommendations, and formatted sections.
    """

    title: str
    """Report title."""

    summary: str
    """Executive summary."""

    generated_at: datetime
    """When report was generated."""

    algorithm: str
    """Algorithm that was run."""

    dataset_info: Dict[str, Any] = field(default_factory=dict)
    """Information about analyzed dataset."""

    insights: List[Insight] = field(default_factory=list)
    """Key insights discovered."""

    recommendations: List[Recommendation] = field(default_factory=list)
    """Actionable recommendations."""

    sections: List[ReportSection] = field(default_factory=list)
    """Report sections."""

    metrics: Dict[str, Any] = field(default_factory=dict)
    """Key metrics and statistics."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "summary": self.summary,
            "generated_at": self.generated_at.isoformat(),
            "algorithm": self.algorithm,
            "dataset_info": self.dataset_info,
            "insights": [i.to_dict() for i in self.insights],
            "recommendations": [r.to_dict() for r in self.recommendations],
            "sections": [s.to_dict() for s in self.sections],
            "metrics": self.metrics,
            "metadata": self.metadata,
        }

    def get_priority_recommendations(
        self, priority: str = "high"
    ) -> List[Recommendation]:
        """Get recommendations by priority."""
        return [r for r in self.recommendations if r.priority == priority]

    def get_critical_insights(self, min_confidence: float = 0.8) -> List[Insight]:
        """Get high-confidence insights."""
        return [i for i in self.insights if i.confidence >= min_confidence]
