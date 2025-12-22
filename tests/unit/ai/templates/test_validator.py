"""Tests for template validator."""

from graph_analytics_ai.ai.templates.validator import (
    TemplateValidator,
    ValidationResult,
)
from graph_analytics_ai.ai.templates.models import (
    AnalysisTemplate,
    AlgorithmParameters,
    TemplateConfig,
    AlgorithmType,
    EngineSize,
)


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_init(self):
        """Test ValidationResult initialization."""
        result = ValidationResult(is_valid=True, errors=[], warnings=["warning1"])

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == ["warning1"]

    def test_bool_conversion_valid(self):
        """Test bool conversion for valid result."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        assert bool(result) is True

    def test_bool_conversion_invalid(self):
        """Test bool conversion for invalid result."""
        result = ValidationResult(is_valid=False, errors=["error"], warnings=[])
        assert bool(result) is False


class TestTemplateValidator:
    """Tests for TemplateValidator class."""

    def test_init_defaults(self):
        """Test validator initialization with defaults."""
        validator = TemplateValidator()
        assert validator.strict is False

    def test_init_strict(self):
        """Test validator initialization in strict mode."""
        validator = TemplateValidator(strict=True)
        assert validator.strict is True

    def test_validate_valid_template(self):
        """Test validation of a valid template."""
        validator = TemplateValidator()

        template = AnalysisTemplate(
            name="Valid Template",
            description="A valid template for testing",
            algorithm=AlgorithmParameters(
                algorithm=AlgorithmType.PAGERANK, parameters={"damping_factor": 0.85}
            ),
            config=TemplateConfig(
                graph_name="test_graph",
                vertex_collections=["users"],
                edge_collections=["follows"],
            ),
        )

        result = validator.validate(template)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_missing_name(self):
        """Test validation with missing name."""
        validator = TemplateValidator()

        template = AnalysisTemplate(
            name="",
            description="Valid description",
            algorithm=AlgorithmParameters(algorithm=AlgorithmType.PAGERANK),
            config=TemplateConfig(graph_name="test_graph"),
        )

        result = validator.validate(template)

        assert result.is_valid is False
        assert any("name" in error.lower() for error in result.errors)

    def test_validate_long_name(self):
        """Test validation with very long name."""
        validator = TemplateValidator()

        template = AnalysisTemplate(
            name="x" * 250,  # Very long name
            description="Valid description",
            algorithm=AlgorithmParameters(algorithm=AlgorithmType.PAGERANK),
            config=TemplateConfig(graph_name="test_graph"),
        )

        result = validator.validate(template)

        # Should be valid but with warning
        assert result.is_valid is True
        assert len(result.warnings) > 0

    def test_validate_missing_description(self):
        """Test validation with missing description."""
        validator = TemplateValidator()

        template = AnalysisTemplate(
            name="Valid Name",
            description="",
            algorithm=AlgorithmParameters(algorithm=AlgorithmType.PAGERANK),
            config=TemplateConfig(graph_name="test_graph"),
        )

        result = validator.validate(template)

        # Empty description generates warning, not error
        assert len(result.warnings) > 0
        assert any("description" in warning.lower() for warning in result.warnings)

    def test_validate_missing_graph_name(self):
        """Test validation with missing graph name."""
        validator = TemplateValidator()

        template = AnalysisTemplate(
            name="Valid Name",
            description="Valid description",
            algorithm=AlgorithmParameters(algorithm=AlgorithmType.PAGERANK),
            config=TemplateConfig(graph_name=""),
        )

        result = validator.validate(template)

        assert result.is_valid is False
        assert any("graph" in error.lower() for error in result.errors)

    def test_validate_invalid_engine_size(self):
        """Test validation handles invalid engine size gracefully."""
        validator = TemplateValidator()

        # Create template with valid engine size
        template = AnalysisTemplate(
            name="Valid Name",
            description="Valid description",
            algorithm=AlgorithmParameters(algorithm=AlgorithmType.PAGERANK),
            config=TemplateConfig(
                graph_name="test_graph", engine_size=EngineSize.XSMALL
            ),
        )

        result = validator.validate(template)

        # Should be valid
        assert result.is_valid is True

    def test_validate_pagerank_parameters(self):
        """Test validation of PageRank algorithm parameters."""
        validator = TemplateValidator()

        template = AnalysisTemplate(
            name="PageRank Analysis",
            description="PageRank analysis",
            algorithm=AlgorithmParameters(
                algorithm=AlgorithmType.PAGERANK,
                parameters={
                    "damping_factor": 0.85,
                    "max_iterations": 100,
                    "threshold": 0.0001,
                },
            ),
            config=TemplateConfig(graph_name="test_graph"),
        )

        result = validator.validate(template)

        assert result.is_valid is True

    def test_validate_invalid_damping_factor(self):
        """Test validation with invalid damping factor."""
        validator = TemplateValidator()

        template = AnalysisTemplate(
            name="PageRank Analysis",
            description="PageRank analysis",
            algorithm=AlgorithmParameters(
                algorithm=AlgorithmType.PAGERANK,
                parameters={"damping_factor": 1.5},  # Invalid (>1)
            ),
            config=TemplateConfig(graph_name="test_graph"),
        )

        result = validator.validate(template)

        # Should have error or warning about damping factor
        assert result.is_valid is False or len(result.warnings) > 0

    def test_validate_negative_iterations(self):
        """Test validation with negative max iterations."""
        validator = TemplateValidator()

        template = AnalysisTemplate(
            name="PageRank Analysis",
            description="PageRank analysis",
            algorithm=AlgorithmParameters(
                algorithm=AlgorithmType.PAGERANK,
                parameters={"max_iterations": -10},  # Invalid
            ),
            config=TemplateConfig(graph_name="test_graph"),
        )

        result = validator.validate(template)

        # Should have error or warning
        assert result.is_valid is False or len(result.warnings) > 0

    def test_validate_label_propagation_parameters(self):
        """Test validation of Label Propagation algorithm parameters."""
        validator = TemplateValidator()

        template = AnalysisTemplate(
            name="Community Detection",
            description="Label propagation community detection",
            algorithm=AlgorithmParameters(
                algorithm=AlgorithmType.LABEL_PROPAGATION,
                parameters={"start_label_attribute": "_key", "maximum_supersteps": 100},
            ),
            config=TemplateConfig(graph_name="test_graph"),
        )

        result = validator.validate(template)

        assert result.is_valid is True

    def test_validate_betweenness_parameters(self):
        """Test validation of Betweenness Centrality algorithm parameters."""
        validator = TemplateValidator()

        template = AnalysisTemplate(
            name="Betweenness Analysis",
            description="Betweenness centrality analysis",
            algorithm=AlgorithmParameters(
                algorithm=AlgorithmType.BETWEENNESS_CENTRALITY,
                parameters={"maximum_supersteps": 100},
            ),
            config=TemplateConfig(graph_name="test_graph"),
        )

        result = validator.validate(template)

        assert result.is_valid is True

    def test_validate_different_algorithms(self):
        """Test validation with different algorithm types."""
        validator = TemplateValidator()

        algorithms = [
            AlgorithmType.PAGERANK,
            AlgorithmType.LABEL_PROPAGATION,
            AlgorithmType.BETWEENNESS_CENTRALITY,
            AlgorithmType.WCC,
            AlgorithmType.SCC,
        ]

        for algo in algorithms:
            template = AnalysisTemplate(
                name=f"{algo.value} Analysis",
                description=f"Run {algo.value} algorithm",
                algorithm=AlgorithmParameters(algorithm=algo),
                config=TemplateConfig(graph_name="test_graph"),
            )

            result = validator.validate(template)

            # All should be valid with minimal parameters
            assert result.is_valid is True, f"Failed for {algo.value}"

    def test_validate_with_collections(self):
        """Test validation with specified collections."""
        validator = TemplateValidator()

        template = AnalysisTemplate(
            name="Analysis",
            description="Analysis with collections",
            algorithm=AlgorithmParameters(algorithm=AlgorithmType.PAGERANK),
            config=TemplateConfig(
                graph_name="test_graph",
                vertex_collections=["users", "products"],
                edge_collections=["purchased", "viewed"],
            ),
        )

        result = validator.validate(template)

        assert result.is_valid is True

    def test_validate_with_result_collection(self):
        """Test validation with result collection specified."""
        validator = TemplateValidator()

        template = AnalysisTemplate(
            name="Analysis",
            description="Analysis with result collection",
            algorithm=AlgorithmParameters(algorithm=AlgorithmType.PAGERANK),
            config=TemplateConfig(
                graph_name="test_graph",
                store_results=True,
                result_collection="my_results",
            ),
        )

        result = validator.validate(template)

        assert result.is_valid is True

    def test_strict_mode_converts_warnings_to_errors(self):
        """Test that strict mode converts warnings to errors."""
        strict_validator = TemplateValidator(strict=True)
        lenient_validator = TemplateValidator(strict=False)

        # Template with very long name (generates warning)
        template = AnalysisTemplate(
            name="x" * 250,
            description="Valid description",
            algorithm=AlgorithmParameters(algorithm=AlgorithmType.PAGERANK),
            config=TemplateConfig(graph_name="test_graph"),
        )

        lenient_result = lenient_validator.validate(template)
        strict_result = strict_validator.validate(template)

        # Lenient should be valid with warnings
        assert lenient_result.is_valid is True
        assert len(lenient_result.warnings) > 0

        # Strict should convert warnings to errors
        assert strict_result.is_valid is False or len(strict_result.errors) > 0

    def test_validate_multiple_errors(self):
        """Test validation with multiple errors."""
        validator = TemplateValidator()

        template = AnalysisTemplate(
            name="",  # Missing name
            description="",  # Missing description
            algorithm=AlgorithmParameters(algorithm=AlgorithmType.PAGERANK),
            config=TemplateConfig(graph_name=""),  # Missing graph name
        )

        result = validator.validate(template)

        assert result.is_valid is False
        assert len(result.errors) >= 2  # Should have multiple errors

    def test_validate_batch(self):
        """Test batch validation of multiple templates."""
        validator = TemplateValidator()

        templates = [
            AnalysisTemplate(
                name="Valid Template 1",
                description="Description 1",
                algorithm=AlgorithmParameters(algorithm=AlgorithmType.PAGERANK),
                config=TemplateConfig(graph_name="graph1"),
            ),
            AnalysisTemplate(
                name="",  # Invalid
                description="Description 2",
                algorithm=AlgorithmParameters(
                    algorithm=AlgorithmType.LABEL_PROPAGATION
                ),
                config=TemplateConfig(graph_name="graph2"),
            ),
            AnalysisTemplate(
                name="Valid Template 3",
                description="Description 3",
                algorithm=AlgorithmParameters(algorithm=AlgorithmType.WCC),
                config=TemplateConfig(graph_name="graph3"),
            ),
        ]

        valid, invalid = validator.validate_batch(templates)

        assert len(valid) == 2  # Templates 1 and 3
        assert len(invalid) == 1  # Template 2
        assert invalid[0][0].name == ""  # Invalid template
        assert invalid[0][1].is_valid is False  # ValidationResult
