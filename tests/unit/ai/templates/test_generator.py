"""Tests for template generator."""

from graph_analytics_ai.ai.templates.generator import (
    TemplateGenerator,
    USE_CASE_TO_ALGORITHM,
)
from graph_analytics_ai.ai.templates.models import (
    AlgorithmType,
    EngineSize,
    AnalysisTemplate,
)
from graph_analytics_ai.ai.generation.use_cases import UseCaseType


class TestUseCaseToAlgorithmMapping:
    """Tests for USE_CASE_TO_ALGORITHM mapping."""

    def test_all_use_case_types_mapped(self):
        """Test that all use case types have algorithm mappings."""
        for use_case_type in UseCaseType:
            assert use_case_type in USE_CASE_TO_ALGORITHM
            assert len(USE_CASE_TO_ALGORITHM[use_case_type]) > 0

    def test_centrality_algorithms(self):
        """Test centrality use case algorithms."""
        algos = USE_CASE_TO_ALGORITHM[UseCaseType.CENTRALITY]
        assert AlgorithmType.PAGERANK in algos

    def test_community_algorithms(self):
        """Test community use case algorithms."""
        algos = USE_CASE_TO_ALGORITHM[UseCaseType.COMMUNITY]
        assert AlgorithmType.WCC in algos
        assert AlgorithmType.SCC in algos
        assert AlgorithmType.LABEL_PROPAGATION in algos


class TestTemplateGenerator:
    """Tests for TemplateGenerator class."""

    def test_init_defaults(self):
        """Test initialization with default parameters."""
        generator = TemplateGenerator()

        assert generator.graph_name == "ecommerce_graph"
        assert generator.default_engine_size == EngineSize.SMALL
        assert generator.auto_optimize is True

    def test_init_custom(self):
        """Test initialization with custom parameters."""
        generator = TemplateGenerator(
            graph_name="social_network",
            default_engine_size=EngineSize.MEDIUM,
            auto_optimize=False,
        )

        assert generator.graph_name == "social_network"
        assert generator.default_engine_size == EngineSize.MEDIUM
        assert generator.auto_optimize is False

    def test_generate_templates_basic(self, simple_use_case):
        """Test basic template generation."""
        generator = TemplateGenerator(graph_name="test_graph")

        templates = generator.generate_templates([simple_use_case])

        assert len(templates) > 0
        assert all(isinstance(t, AnalysisTemplate) for t in templates)

    def test_generate_templates_with_schema(self, simple_use_case, simple_schema):
        """Test template generation with schema."""
        generator = TemplateGenerator(graph_name="test_graph")

        templates = generator.generate_templates(
            [simple_use_case], schema=simple_schema
        )

        assert len(templates) > 0
        for template in templates:
            assert template.config.graph_name == "test_graph"

    def test_generate_templates_empty_use_cases(self):
        """Test generating templates with empty use case list."""
        generator = TemplateGenerator(graph_name="test_graph")

        templates = generator.generate_templates([])

        assert templates == []

    def test_template_has_required_fields(self, simple_use_case):
        """Test that generated templates have all required fields."""
        generator = TemplateGenerator(graph_name="test_graph")

        templates = generator.generate_templates([simple_use_case])

        for template in templates:
            assert len(template.name) > 0
            assert len(template.description) > 0
            assert template.algorithm is not None
            assert template.config is not None

    def test_template_includes_use_case_id(self, simple_use_case):
        """Test that templates include use case ID."""
        generator = TemplateGenerator(graph_name="test_graph")

        templates = generator.generate_templates([simple_use_case])

        for template in templates:
            assert template.use_case_id == "UC-001"

    def test_different_use_case_types(self):
        """Test template generation for different use case types."""
        from graph_analytics_ai.ai.generation.use_cases import UseCase
        from graph_analytics_ai.ai.documents.models import Priority

        generator = TemplateGenerator(graph_name="test_graph")

        use_case_types = [
            UseCaseType.CENTRALITY,
            UseCaseType.COMMUNITY,
            UseCaseType.PATHFINDING,
        ]

        for use_case_type in use_case_types:
            use_case = UseCase(
                id=f"UC-{use_case_type.value}",
                title=f"Test {use_case_type.value}",
                description="Test",
                use_case_type=use_case_type,
                priority=Priority.MEDIUM,
                related_requirements=[],
                graph_algorithms=[],
                data_needs=["users"],
            )

            templates = generator.generate_templates([use_case])

            assert len(templates) > 0, f"No templates for {use_case_type.value}"

            # Verify algorithms match use case type
            expected_algos = USE_CASE_TO_ALGORITHM[use_case_type]
            for template in templates:
                assert template.algorithm.algorithm in expected_algos
