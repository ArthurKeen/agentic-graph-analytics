"""
Unit tests for PRD generator.
"""

from graph_analytics_ai.ai.generation.prd import (
    PRDGenerator,
    generate_prd_markdown,
)


class TestPRDGenerator:
    """Test PRDGenerator behaviors."""

    def test_generate_minimal(self, sample_extracted_requirements):
        gen = PRDGenerator(include_schema_summary=False)
        md = gen.generate_prd(
            sample_extracted_requirements, product_name="Test Product"
        )

        assert "# Product Requirements Document" in md
        assert "Test Product" in md
        assert "Objectives" in md
        assert "Requirements" in md
        # Should list at least one requirement id
        assert "REQ-001" in md

    def test_generate_with_schema(
        self, sample_extracted_requirements, sample_graph_schema
    ):
        gen = PRDGenerator(include_schema_summary=True)
        md = gen.generate_prd(
            sample_extracted_requirements,
            schema=sample_graph_schema,
            schema_analysis=None,
        )

        assert "Graph Schema" in md
        assert "Vertex collections" in md
        assert "users" in md  # from sample schema

    def test_generate_with_analysis(
        self, sample_extracted_requirements, sample_graph_schema, mock_llm_provider
    ):
        # Use a fake analysis object
        from graph_analytics_ai.ai.schema.models import SchemaAnalysis

        analysis = SchemaAnalysis(
            schema=sample_graph_schema,
            description="Test graph",
            domain="test-domain",
            key_entities=["users"],
            key_relationships=["follows"],
            suggested_analyses=[{"title": "PageRank"}],
            complexity_score=4.2,
        )

        gen = PRDGenerator(include_schema_summary=True)
        md = gen.generate_prd(
            sample_extracted_requirements,
            schema=sample_graph_schema,
            schema_analysis=analysis,
        )

        assert "test-domain" in md
        assert "PageRank" in md
        assert "4.2/10" in md

    def test_generate_prd_markdown_helper(self, sample_extracted_requirements):
        md = generate_prd_markdown(sample_extracted_requirements)
        assert md.startswith("# Product Requirements Document")


class TestOrderingAndContent:
    """Ensure ordering and priority handling."""

    def test_requirements_sorted_by_priority(self, sample_extracted_requirements):
        # Shuffle requirements to ensure sorting happens
        sample_extracted_requirements.requirements = list(
            reversed(sample_extracted_requirements.requirements)
        )

        gen = PRDGenerator(include_schema_summary=False)
        md = gen.generate_prd(sample_extracted_requirements)

        # Critical first, then high, etc.
        critical_index = md.index("REQ-001")
        high_index = md.index("REQ-002")
        assert critical_index < high_index

    def test_handles_empty_collections(
        self, sample_extracted_requirements, sample_graph_schema
    ):
        # Remove constraints/risks to exercise empty paths
        sample_extracted_requirements.constraints = []
        sample_extracted_requirements.risks = []

        gen = PRDGenerator(
            include_schema_summary=True, include_constraints=True, include_risks=True
        )
        md = gen.generate_prd(sample_extracted_requirements, schema=sample_graph_schema)

        assert "_No constraints identified._" in md
        assert "_No risks identified._" in md
