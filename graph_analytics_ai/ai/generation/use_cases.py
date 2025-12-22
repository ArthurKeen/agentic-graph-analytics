"""
Use case generation from extracted requirements and schema analysis.

Generates actionable graph analytics use cases that map requirements
to specific analytics algorithms and expected outputs.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

from ..documents.models import ExtractedRequirements, Requirement, Priority
from ..schema.models import SchemaAnalysis


class UseCaseType(Enum):
    """Type of graph analytics use case."""

    CENTRALITY = "centrality"
    COMMUNITY = "community"
    PATHFINDING = "pathfinding"
    PATTERN = "pattern"
    ANOMALY = "anomaly"
    RECOMMENDATION = "recommendation"
    SIMILARITY = "similarity"


@dataclass
class UseCase:
    """Represents a single graph analytics use case."""

    id: str
    """Unique identifier (e.g., UC-001)."""

    title: str
    """Human-readable title."""

    description: str
    """What this use case accomplishes."""

    use_case_type: UseCaseType
    """Type of analytics."""

    priority: Priority
    """Priority level."""

    related_requirements: List[str] = field(default_factory=list)
    """IDs of related requirements."""

    graph_algorithms: List[str] = field(default_factory=list)
    """Suggested algorithms (e.g., PageRank, WCC, Label Propagation)."""

    data_needs: List[str] = field(default_factory=list)
    """What data/collections are needed."""

    expected_outputs: List[str] = field(default_factory=list)
    """What results to expect."""

    success_metrics: List[str] = field(default_factory=list)
    """How to measure success."""


class UseCaseGenerator:
    """
    Generates graph analytics use cases from requirements and schema.

    This is a deterministic generator that creates sensible use cases
    based on requirement types and schema structure. It can be enhanced
    later with LLM-powered generation for richer descriptions.

    Example:
        >>> from graph_analytics_ai.ai.generation import UseCaseGenerator
        >>>
        >>> generator = UseCaseGenerator()
        >>> use_cases = generator.generate(extracted_requirements, schema_analysis)
        >>>
        >>> for uc in use_cases:
        ...     print(f"{uc.id}: {uc.title} [{uc.use_case_type.value}]")
    """

    def __init__(self, max_use_cases: int = 10):
        """
        Initialize use case generator.

        Args:
            max_use_cases: Maximum number of use cases to generate.
        """
        self.max_use_cases = max_use_cases

    def generate(
        self,
        extracted: ExtractedRequirements,
        schema_analysis: Optional[SchemaAnalysis] = None,
    ) -> List[UseCase]:
        """
        Generate use cases from requirements and optional schema analysis.

        Args:
            extracted: Extracted requirements from Phase 3.
            schema_analysis: Optional schema analysis from Phase 2.

        Returns:
            List of UseCase objects.
        """
        use_cases = []

        # Generate from objectives
        for obj in extracted.objectives[: self.max_use_cases]:
            uc = self._use_case_from_objective(obj, extracted)
            if uc:
                use_cases.append(uc)

        # Generate from schema analysis suggestions if available
        if schema_analysis and schema_analysis.suggested_analyses:
            for i, suggestion in enumerate(schema_analysis.suggested_analyses):
                if len(use_cases) >= self.max_use_cases:
                    break
                uc = self._use_case_from_suggestion(
                    suggestion, i, extracted, schema_analysis
                )
                if uc:
                    use_cases.append(uc)

        # Generate from high-priority requirements if we have room
        high_pri_reqs = [r for r in extracted.requirements if r.is_high_priority]
        for i, req in enumerate(high_pri_reqs):
            if len(use_cases) >= self.max_use_cases:
                break
            uc = self._use_case_from_requirement(req, i, extracted)
            if uc:
                use_cases.append(uc)

        return use_cases[: self.max_use_cases]

    def _use_case_from_objective(
        self, obj, extracted: ExtractedRequirements
    ) -> Optional[UseCase]:
        """Create use case from an objective."""
        # Map objective to use case type based on keywords
        title_lower = obj.title.lower()
        desc_lower = obj.description.lower()

        combined_text = title_lower + " " + desc_lower
        use_case_type = self._infer_use_case_type(combined_text)

        # DEBUG LOGGING - Show classification decision
        print(f"\n[USE CASE DEBUG] Classifying objective: {obj.title}")
        print(f"  Combined text: {combined_text[:100]}...")
        print(f"  Inferred type: {use_case_type}")

        return UseCase(
            id=obj.id.replace("OBJ-", "UC-"),
            title=obj.title,
            description=obj.description,
            use_case_type=use_case_type,
            priority=obj.priority,
            related_requirements=obj.related_requirements,
            data_needs=self._extract_data_needs(obj.description, extracted),
            expected_outputs=obj.success_criteria,
            success_metrics=obj.metrics if hasattr(obj, "metrics") else [],
        )

    def _use_case_from_suggestion(
        self,
        suggestion: Dict[str, Any],
        index: int,
        extracted: ExtractedRequirements,
        schema_analysis: SchemaAnalysis,
    ) -> Optional[UseCase]:
        """Create use case from schema analysis suggestion."""
        sug_type = suggestion.get("type", "analysis")
        title = suggestion.get("title", f"Graph Analysis {index + 1}")
        reason = suggestion.get("reason", "")

        # Map algorithm/suggestion type to use case type
        use_case_type = self._map_algorithm_to_type(sug_type)

        # CRITICAL FIX: Check title for household/clustering keywords
        # Even if suggestion type maps to CENTRALITY, household resolution is COMMUNITY!
        title_lower = title.lower()
        if any(
            k in title_lower
            for k in ["household", "identity resolution", "clustering", "grouping"]
        ):
            print(
                "[USE CASE DEBUG] OVERRIDE: Detected household/clustering keywords in title"
            )
            print(f"  Original mapping: {use_case_type}")
            use_case_type = UseCaseType.COMMUNITY
            print(f"  Overridden to: {use_case_type}")

        # DEBUG LOGGING - Show classification decision
        print("\n[USE CASE DEBUG] Creating use case from suggestion:")
        print(f"  Title: {title}")
        print(f"  Suggestion type: {sug_type}")
        print(f"  Final use case type: {use_case_type}")

        # Infer data needs from schema
        data_needs = []
        if schema_analysis.key_entities:
            data_needs.append(
                f"Vertex collections: {', '.join(schema_analysis.key_entities)}"
            )
        if schema_analysis.key_relationships:
            data_needs.append(
                f"Edge collections: {', '.join(schema_analysis.key_relationships)}"
            )

        return UseCase(
            id=f"UC-S{index + 1:02d}",
            title=title,
            description=reason,
            use_case_type=use_case_type,
            priority=Priority.MEDIUM,
            related_requirements=[],
            graph_algorithms=[sug_type],
            data_needs=data_needs,
            expected_outputs=[f"{title} results"],
            success_metrics=[],
        )

    def _use_case_from_requirement(
        self, req: Requirement, index: int, extracted: ExtractedRequirements
    ) -> Optional[UseCase]:
        """Create use case from a requirement."""
        use_case_type = self._infer_use_case_type(req.text)

        return UseCase(
            id=f"UC-R{index + 1:02d}",
            title=f"Requirement: {req.id}",
            description=req.text,
            use_case_type=use_case_type,
            priority=req.priority,
            related_requirements=[req.id],
            data_needs=[],
            expected_outputs=[],
            success_metrics=[],
        )

    def _infer_use_case_type(self, text: str) -> UseCaseType:
        """Infer use case type from text content."""
        text_lower = text.lower()

        # Check more specific keywords first to avoid false positives
        # Anomaly/fraud detection (check before pattern)
        if any(
            k in text_lower for k in ["anomaly", "fraud", "outlier", "unusual", "risk"]
        ):
            return UseCaseType.ANOMALY

        # Community detection (check before centrality to catch "group")
        # CRITICAL: Includes "household", "identity resolution", "grouping"
        # These are clustering/community detection problems, NOT centrality!
        if any(
            k in text_lower
            for k in [
                "community",
                "communit",
                "cluster",
                "segment",
                "household",
                "identity resolution",
                "grouping",
                "group devices",
            ]
        ):
            return UseCaseType.COMMUNITY

        # Path finding
        elif any(k in text_lower for k in ["path", "route", "shortest", "connection"]):
            return UseCaseType.PATHFINDING

        # Pattern detection
        elif any(k in text_lower for k in ["pattern", "motif", "structure"]):
            return UseCaseType.PATTERN

        # Recommendation
        elif any(k in text_lower for k in ["recommend", "suggest"]):
            return UseCaseType.RECOMMENDATION

        # Similarity
        elif any(k in text_lower for k in ["similar", "resembl", "match"]):
            return UseCaseType.SIMILARITY

        # Centrality (last, as it's more general)
        elif any(
            k in text_lower
            for k in ["influential", "important", "central", "rank", "authority"]
        ):
            return UseCaseType.CENTRALITY

        # Default
        return UseCaseType.CENTRALITY

    def _map_algorithm_to_type(self, algorithm: str) -> UseCaseType:
        """Map algorithm name to use case type."""
        alg_lower = algorithm.lower()

        if (
            "pagerank" in alg_lower
            or "betweenness" in alg_lower
            or "centrality" in alg_lower
        ):
            return UseCaseType.CENTRALITY
        elif (
            "community" in alg_lower
            or "cluster" in alg_lower
            or "modularity" in alg_lower
            or "propagation" in alg_lower
        ):
            return UseCaseType.COMMUNITY
        elif "shortest" in alg_lower or "path" in alg_lower or "dijkstra" in alg_lower:
            return UseCaseType.PATHFINDING
        elif "pattern" in alg_lower or "motif" in alg_lower:
            return UseCaseType.PATTERN
        elif "anomaly" in alg_lower or "outlier" in alg_lower:
            return UseCaseType.ANOMALY

        return UseCaseType.CENTRALITY

    def _extract_data_needs(
        self, text: str, extracted: ExtractedRequirements
    ) -> List[str]:
        """Extract data needs from text by looking for collection/entity mentions."""
        # Simple heuristic: look for capitalized words that might be entity names
        # This can be enhanced with NER or schema matching
        needs = []

        # If domain is known, add it as context
        if extracted.domain:
            needs.append(f"Domain: {extracted.domain}")

        return needs


def generate_use_cases(
    extracted: ExtractedRequirements,
    schema_analysis: Optional[SchemaAnalysis] = None,
    max_use_cases: int = 10,
) -> List[UseCase]:
    """
    Convenience function to generate use cases.

    Args:
        extracted: Extracted requirements.
        schema_analysis: Optional schema analysis.
        max_use_cases: Maximum number to generate.

    Returns:
        List of UseCase objects.

    Example:
        >>> use_cases = generate_use_cases(extracted_requirements, analysis)
        >>> for uc in use_cases:
        ...     print(f"{uc.id}: {uc.title}")
    """
    generator = UseCaseGenerator(max_use_cases=max_use_cases)
    return generator.generate(extracted, schema_analysis)
