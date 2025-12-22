"""
Test for household clustering classification bug fix.

Verifies that "Household Identity Resolution" use cases are correctly
classified as COMMUNITY (clustering) instead of CENTRALITY (ranking).
"""

from graph_analytics_ai.ai.generation.use_cases import UseCaseGenerator, UseCaseType
from graph_analytics_ai.ai.documents.models import (
    ExtractedRequirements,
    Objective,
    Priority,
)


def test_household_clustering_classification():
    """
    CRITICAL BUG FIX TEST:
    Verify household use cases are classified as COMMUNITY, not CENTRALITY.

    Root Cause: "Household Identity Resolution" contains neither "cluster"
    nor "segment" keywords, so it was falling through to CENTRALITY default.

    Fix: Added "household", "identity resolution", "grouping" to COMMUNITY keywords.
    """

    generator = UseCaseGenerator()

    # Create an objective that looks like household resolution
    household_objective = Objective(
        id="OBJ-001",
        title="Household Identity Resolution",
        description="Group devices into households to understand cross-device behavior",
        priority=Priority.HIGH,
        related_requirements=[],
        success_criteria=["Devices grouped into household clusters"],
    )

    extracted = ExtractedRequirements(
        documents=[],  # Required field
        summary="Ad tech analytics",
        domain="advertising",
        objectives=[household_objective],
        requirements=[],
        stakeholders=[],
    )

    # Generate use case from objective
    use_case = generator._use_case_from_objective(household_objective, extracted)

    # CRITICAL ASSERTION: Should be COMMUNITY (clustering), not CENTRALITY (ranking)
    assert (
        use_case.use_case_type == UseCaseType.COMMUNITY
    ), f"Household clustering should be COMMUNITY, got {use_case.use_case_type}"


def test_identity_resolution_classification():
    """Verify any "identity resolution" use case is classified as COMMUNITY."""

    generator = UseCaseGenerator()

    objective = Objective(
        id="OBJ-002",
        title="Device Identity Resolution",
        description="Resolve device identities across different contexts",
        priority=Priority.HIGH,
        related_requirements=[],
        success_criteria=["Devices correctly grouped"],
    )

    extracted = ExtractedRequirements(
        documents=[],
        summary="Test",
        domain="test",
        objectives=[objective],
        requirements=[],
        stakeholders=[],
    )

    use_case = generator._use_case_from_objective(objective, extracted)

    assert (
        use_case.use_case_type == UseCaseType.COMMUNITY
    ), f"Identity resolution should be COMMUNITY, got {use_case.use_case_type}"


def test_grouping_classification():
    """Verify "grouping" use cases are classified as COMMUNITY."""

    generator = UseCaseGenerator()

    objective = Objective(
        id="OBJ-003",
        title="Group Devices by Behavior",
        description="Grouping devices based on usage patterns",
        priority=Priority.MEDIUM,
        related_requirements=[],
        success_criteria=["Devices grouped"],
    )

    extracted = ExtractedRequirements(
        documents=[],
        summary="Test",
        domain="test",
        objectives=[objective],
        requirements=[],
        stakeholders=[],
    )

    use_case = generator._use_case_from_objective(objective, extracted)

    assert (
        use_case.use_case_type == UseCaseType.COMMUNITY
    ), f"Grouping should be COMMUNITY, got {use_case.use_case_type}"


def test_clustering_still_works():
    """Verify existing "clustering" keyword still works."""

    generator = UseCaseGenerator()

    objective = Objective(
        id="OBJ-004",
        title="Customer Clustering",
        description="Cluster customers by purchase behavior",
        priority=Priority.MEDIUM,
        related_requirements=[],
        success_criteria=["Customers clustered"],
    )

    extracted = ExtractedRequirements(
        documents=[],
        summary="Test",
        domain="test",
        objectives=[objective],
        requirements=[],
        stakeholders=[],
    )

    use_case = generator._use_case_from_objective(objective, extracted)

    assert use_case.use_case_type == UseCaseType.COMMUNITY


def test_centrality_still_works():
    """Verify legitimate CENTRALITY use cases still classified correctly."""

    generator = UseCaseGenerator()

    objective = Objective(
        id="OBJ-005",
        title="Identify Influential Publishers",
        description="Rank publishers by influence and reach",
        priority=Priority.MEDIUM,
        related_requirements=[],
        success_criteria=["Publishers ranked"],
    )

    extracted = ExtractedRequirements(
        documents=[],
        summary="Test",
        domain="test",
        objectives=[objective],
        requirements=[],
        stakeholders=[],
    )

    use_case = generator._use_case_from_objective(objective, extracted)

    assert (
        use_case.use_case_type == UseCaseType.CENTRALITY
    ), f"Influence ranking should be CENTRALITY, got {use_case.use_case_type}"


def test_suggestion_title_override():
    """
    Test that title-based override works for suggestions.

    Even if LLM suggests a centrality-type algorithm, if the title
    contains "household" or "clustering", it should be COMMUNITY.
    """
    from graph_analytics_ai.ai.schema.models import SchemaAnalysis, GraphSchema

    generator = UseCaseGenerator()

    # Simulate LLM suggesting "pagerank" for household resolution
    # (This is what was happening in production!)
    suggestion = {
        "type": "pagerank",  # Wrong algorithm type
        "title": "Household Identity Clustering",  # But title is clear!
        "reason": "Identify household structures",
    }

    extracted = ExtractedRequirements(
        documents=[],
        summary="Test",
        domain="test",
        objectives=[],
        requirements=[],
        stakeholders=[],
    )

    # Create minimal schema
    schema = GraphSchema(
        database_name="test_db", vertex_collections={}, edge_collections={}
    )

    schema_analysis = SchemaAnalysis(
        schema=schema,
        description="Test schema",
        domain="test",
        complexity_score=5,
        key_entities=["Device", "IP"],
        key_relationships=["SEEN_ON_IP"],
    )

    use_case = generator._use_case_from_suggestion(
        suggestion, 0, extracted, schema_analysis
    )

    # CRITICAL: Should override to COMMUNITY despite "pagerank" type
    assert (
        use_case.use_case_type == UseCaseType.COMMUNITY
    ), f"Title-based override failed: got {use_case.use_case_type}"
