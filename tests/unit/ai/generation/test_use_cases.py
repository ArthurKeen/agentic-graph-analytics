"""
Unit tests for use case generator.
"""

from graph_analytics_ai.ai.generation.use_cases import (
    UseCaseGenerator,
    UseCaseType,
    generate_use_cases,
)


class TestUseCaseGenerator:
    """Test UseCaseGenerator behaviors."""

    def test_generate_from_objectives(self, sample_extracted_requirements):
        """Test generating use cases from objectives."""
        gen = UseCaseGenerator(max_use_cases=10)
        use_cases = gen.generate(sample_extracted_requirements)

        assert len(use_cases) > 0

        # Should have IDs
        for uc in use_cases:
            assert uc.id.startswith("UC-")
            assert uc.title != ""
            assert uc.description != ""

    def test_generate_with_schema_analysis(
        self, sample_extracted_requirements, sample_graph_schema
    ):
        """Test generating use cases with schema analysis."""
        from graph_analytics_ai.ai.schema.models import SchemaAnalysis

        analysis = SchemaAnalysis(
            schema=sample_graph_schema,
            description="Test graph",
            domain="test-domain",
            key_entities=["users"],
            key_relationships=["follows"],
            suggested_analyses=[
                {
                    "type": "pagerank",
                    "title": "PageRank",
                    "reason": "Find influential users",
                },
                {
                    "type": "community_detection",
                    "title": "Communities",
                    "reason": "Find clusters",
                },
            ],
            complexity_score=4.0,
        )

        gen = UseCaseGenerator(max_use_cases=10)
        use_cases = gen.generate(
            sample_extracted_requirements, schema_analysis=analysis
        )

        assert len(use_cases) > 0

        # Should include schema-derived use cases
        schema_uc = [uc for uc in use_cases if uc.id.startswith("UC-S")]
        assert len(schema_uc) > 0

        # Check one has the right properties
        pagerank_uc = next((uc for uc in schema_uc if "PageRank" in uc.title), None)
        assert pagerank_uc is not None
        assert pagerank_uc.use_case_type == UseCaseType.CENTRALITY

    def test_max_use_cases_limit(self, sample_extracted_requirements):
        """Test that max_use_cases limit is respected."""
        gen = UseCaseGenerator(max_use_cases=3)
        use_cases = gen.generate(sample_extracted_requirements)

        assert len(use_cases) <= 3

    def test_generate_use_cases_helper(self, sample_extracted_requirements):
        """Test convenience function."""
        use_cases = generate_use_cases(sample_extracted_requirements, max_use_cases=5)

        assert isinstance(use_cases, list)
        assert len(use_cases) <= 5


class TestUseCaseTypeInference:
    """Test use case type inference logic."""

    def test_infer_centrality(self):
        """Test inferring centrality use case."""
        gen = UseCaseGenerator()

        uc_type = gen._infer_use_case_type("Find the most influential users")
        assert uc_type == UseCaseType.CENTRALITY

        uc_type = gen._infer_use_case_type("Rank nodes by importance")
        assert uc_type == UseCaseType.CENTRALITY

    def test_infer_community(self):
        """Test inferring community detection."""
        gen = UseCaseGenerator()

        uc_type = gen._infer_use_case_type("Identify user communities")
        assert uc_type == UseCaseType.COMMUNITY

        uc_type = gen._infer_use_case_type("Segment customers into groups")
        assert uc_type == UseCaseType.COMMUNITY

    def test_infer_pathfinding(self):
        """Test inferring pathfinding use case."""
        gen = UseCaseGenerator()

        uc_type = gen._infer_use_case_type("Find shortest path between nodes")
        assert uc_type == UseCaseType.PATHFINDING

        uc_type = gen._infer_use_case_type("Route connections efficiently")
        assert uc_type == UseCaseType.PATHFINDING

    def test_infer_anomaly(self):
        """Test inferring anomaly detection."""
        gen = UseCaseGenerator()

        uc_type = gen._infer_use_case_type("Detect fraudulent transactions")
        assert uc_type == UseCaseType.ANOMALY

        uc_type = gen._infer_use_case_type("Identify unusual patterns and risks")
        assert uc_type == UseCaseType.ANOMALY

    def test_map_algorithm_to_type(self):
        """Test mapping algorithm names to types."""
        gen = UseCaseGenerator()

        assert gen._map_algorithm_to_type("pagerank") == UseCaseType.CENTRALITY
        assert (
            gen._map_algorithm_to_type("community_detection") == UseCaseType.COMMUNITY
        )
        assert gen._map_algorithm_to_type("shortest_path") == UseCaseType.PATHFINDING


class TestUseCaseContent:
    """Test use case content and properties."""

    def test_use_case_from_objective(self, sample_extracted_requirements):
        """Test creating use case from objective."""
        gen = UseCaseGenerator()

        obj = sample_extracted_requirements.objectives[0]
        uc = gen._use_case_from_objective(obj, sample_extracted_requirements)

        assert uc is not None
        assert uc.id.startswith("UC-")
        assert uc.title == obj.title
        assert uc.description == obj.description
        assert uc.priority == obj.priority
        assert uc.related_requirements == obj.related_requirements

    def test_use_case_includes_data_needs(
        self, sample_extracted_requirements, sample_graph_schema
    ):
        """Test that use cases include data needs from schema."""
        from graph_analytics_ai.ai.schema.models import SchemaAnalysis

        analysis = SchemaAnalysis(
            schema=sample_graph_schema,
            description="Test",
            domain="test",
            key_entities=["users", "products"],
            key_relationships=["follows"],
            suggested_analyses=[
                {"type": "pagerank", "title": "PageRank", "reason": "Test"}
            ],
            complexity_score=4.0,
        )

        gen = UseCaseGenerator()
        use_cases = gen.generate(
            sample_extracted_requirements, schema_analysis=analysis
        )

        # Schema-derived use cases should have data needs
        schema_uc = [uc for uc in use_cases if uc.id.startswith("UC-S")]
        if schema_uc:
            assert any(len(uc.data_needs) > 0 for uc in schema_uc)
