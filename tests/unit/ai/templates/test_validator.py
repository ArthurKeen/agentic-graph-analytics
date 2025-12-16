"""Tests for template validator."""

import pytest
from graph_analytics_ai.ai.templates.validator import (
    TemplateValidator,
    ValidationResult,
    validate_template
)
from graph_analytics_ai.ai.templates.models import (
    AnalysisTemplate,
    AlgorithmParameters,
    TemplateConfig,
    AlgorithmType,
    EngineSize
)


class TestValidationResult:
    """Tests for ValidationResult dataclass."""
    
    def test_init_valid(self):
        """Test initialization of valid result."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["warning1"]
        )
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
    
    def test_init_invalid(self):
        """Test initialization of invalid result."""
        result = ValidationResult(
            is_valid=False,
            errors=["error1", "error2"],
            warnings=[]
        )
        
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 0
    
    def test_bool_conversion(self):
        """Test truth value conversion."""
        valid_result = ValidationResult(is_valid=True, errors=[], warnings=[])
        invalid_result = ValidationResult(is_valid=False, errors=["error"], warnings=[])
        
        assert bool(valid_result) is True
        assert bool(invalid_result) is False
        
        # Can use in if statements
        if valid_result:
            passed = True
        assert passed is True


class TestTemplateValidator:
    """Tests for TemplateValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create a validator for testing."""
        return TemplateValidator(strict=False)
    
    @pytest.fixture
    def strict_validator(self):
        """Create a strict validator for testing."""
        return TemplateValidator(strict=True)
    
    @pytest.fixture
    def valid_template(self):
        """Create a valid template for testing."""
        algorithm = AlgorithmParameters(
            algorithm=AlgorithmType.PAGERANK,
            parameters={"threshold": 0.0001, "max_iterations": 100, "damping_factor": 0.85}
        )
        
        config = TemplateConfig(
            graph_name="test_graph",
            vertex_collections=["users"],
            edge_collections=["follows"],
            engine_size=EngineSize.SMALL,
            store_results=True,
            result_collection="results"
        )
        
        return AnalysisTemplate(
            name="Valid Template",
            description="A valid template for testing",
            algorithm=algorithm,
            config=config,
            estimated_runtime_seconds=10.0
        )
    
    def test_init_defaults(self):
        """Test validator initialization with defaults."""
        validator = TemplateValidator()
        assert validator.strict is False
    
    def test_init_strict(self):
        """Test validator initialization in strict mode."""
        validator = TemplateValidator(strict=True)
        assert validator.strict is True
    
    def test_validate_valid_template(self, validator, valid_template):
        """Test validation of a valid template."""
        result = validator.validate(valid_template)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_empty_name(self, validator, valid_template):
        """Test validation fails with empty name."""
        valid_template.name = ""
        result = validator.validate(valid_template)
        
        assert result.is_valid is False
        assert any("name" in error.lower() for error in result.errors)
    
    def test_validate_whitespace_name(self, validator, valid_template):
        """Test validation fails with whitespace-only name."""
        valid_template.name = "   "
        result = validator.validate(valid_template)
        
        assert result.is_valid is False
        assert any("name" in error.lower() for error in result.errors)
    
    def test_validate_long_name_warning(self, validator, valid_template):
        """Test validation warns about very long names."""
        valid_template.name = "x" * 250
        result = validator.validate(valid_template)
        
        assert result.is_valid is True  # Warning, not error
        assert len(result.warnings) > 0
        assert any("long" in warning.lower() for warning in result.warnings)
    
    def test_validate_empty_description_warning(self, validator, valid_template):
        """Test validation warns about empty description."""
        valid_template.description = ""
        result = validator.validate(valid_template)
        
        assert result.is_valid is True  # Warning, not error
        assert len(result.warnings) > 0
        assert any("description" in warning.lower() for warning in result.warnings)
    
    def test_validate_empty_graph_name(self, validator, valid_template):
        """Test validation fails with empty graph name."""
        valid_template.config.graph_name = ""
        result = validator.validate(valid_template)
        
        assert result.is_valid is False
        assert any("graph name" in error.lower() for error in result.errors)
    
    def test_validate_invalid_engine_size(self, validator, valid_template):
        """Test validation with invalid engine size."""
        # This is harder to test since EngineSize is an enum
        # but we can mock it
        valid_template.config.engine_size = "invalid"  # type: ignore
        result = validator.validate(valid_template)
        
        assert result.is_valid is False
        assert any("engine size" in error.lower() for error in result.errors)
    
    def test_validate_pagerank_invalid_damping(self, validator, valid_template):
        """Test validation of PageRank with invalid damping factor."""
        valid_template.algorithm.parameters["damping_factor"] = 1.5  # Invalid (must be < 1)
        result = validator.validate(valid_template)
        
        assert result.is_valid is False
        assert any("damping" in error.lower() for error in result.errors)
    
    def test_validate_pagerank_negative_threshold(self, validator, valid_template):
        """Test validation of PageRank with negative threshold."""
        valid_template.algorithm.parameters["threshold"] = -0.001
        result = validator.validate(valid_template)
        
        assert result.is_valid is False
        assert any("threshold" in error.lower() for error in result.errors)
    
    def test_validate_pagerank_high_threshold_warning(self, validator, valid_template):
        """Test validation warns about high PageRank threshold."""
        valid_template.algorithm.parameters["threshold"] = 0.2
        result = validator.validate(valid_template)
        
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert any("threshold" in warning.lower() for warning in result.warnings)
    
    def test_validate_pagerank_negative_iterations(self, validator, valid_template):
        """Test validation fails with negative max iterations."""
        valid_template.algorithm.parameters["max_iterations"] = -10
        result = validator.validate(valid_template)
        
        assert result.is_valid is False
        assert any("max_iterations" in error.lower() for error in result.errors)
    
    def test_validate_pagerank_high_iterations_warning(self, validator, valid_template):
        """Test validation warns about very high iterations."""
        valid_template.algorithm.parameters["max_iterations"] = 600
        result = validator.validate(valid_template)
        
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert any("iterations" in warning.lower() for warning in result.warnings)
    
    def test_validate_louvain_negative_resolution(self, validator, valid_template):
        """Test validation of Louvain with negative resolution."""
        valid_template.algorithm = AlgorithmParameters(
            algorithm=AlgorithmType.LOUVAIN,
            parameters={"resolution": -1.0}
        )
        result = validator.validate(valid_template)
        
        assert result.is_valid is False
        assert any("resolution" in error.lower() for error in result.errors)
    
    def test_validate_louvain_high_resolution_warning(self, validator, valid_template):
        """Test validation warns about high Louvain resolution."""
        valid_template.algorithm = AlgorithmParameters(
            algorithm=AlgorithmType.LOUVAIN,
            parameters={"resolution": 6.0}
        )
        result = validator.validate(valid_template)
        
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert any("resolution" in warning.lower() for warning in result.warnings)
    
    def test_validate_louvain_invalid_min_community_size(self, validator, valid_template):
        """Test validation of Louvain with invalid min community size."""
        valid_template.algorithm = AlgorithmParameters(
            algorithm=AlgorithmType.LOUVAIN,
            parameters={"min_community_size": 0}
        )
        result = validator.validate(valid_template)
        
        assert result.is_valid is False
        assert any("min_community_size" in error.lower() for error in result.errors)
    
    def test_validate_shortest_path_invalid_direction(self, validator, valid_template):
        """Test validation of shortest path with invalid direction."""
        valid_template.algorithm = AlgorithmParameters(
            algorithm=AlgorithmType.SHORTEST_PATH,
            parameters={"direction": "invalid"}
        )
        result = validator.validate(valid_template)
        
        assert result.is_valid is False
        assert any("direction" in error.lower() for error in result.errors)
    
    def test_validate_centrality_non_boolean_normalized(self, validator, valid_template):
        """Test validation of centrality with non-boolean normalized."""
        valid_template.algorithm = AlgorithmParameters(
            algorithm=AlgorithmType.BETWEENNESS_CENTRALITY,
            parameters={"normalized": "yes"}  # Should be boolean
        )
        result = validator.validate(valid_template)
        
        assert result.is_valid is False
        assert any("normalized" in error.lower() for error in result.errors)
    
    def test_validate_negative_runtime(self, validator, valid_template):
        """Test validation fails with negative estimated runtime."""
        valid_template.estimated_runtime_seconds = -10.0
        result = validator.validate(valid_template)
        
        assert result.is_valid is False
        assert any("runtime" in error.lower() for error in result.errors)
    
    def test_validate_very_long_runtime_warning(self, validator, valid_template):
        """Test validation warns about very long runtime."""
        valid_template.estimated_runtime_seconds = 5000.0  # > 1 hour
        result = validator.validate(valid_template)
        
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert any("runtime" in warning.lower() for warning in result.warnings)
    
    def test_validate_empty_vertex_collection(self, validator, valid_template):
        """Test validation fails with empty vertex collection name."""
        valid_template.config.vertex_collections = ["users", ""]
        result = validator.validate(valid_template)
        
        assert result.is_valid is False
        assert any("vertex collection" in error.lower() for error in result.errors)
    
    def test_validate_vertex_collection_with_spaces(self, validator, valid_template):
        """Test validation fails with spaces in vertex collection name."""
        valid_template.config.vertex_collections = ["user data"]
        result = validator.validate(valid_template)
        
        assert result.is_valid is False
        assert any("vertex collection" in error.lower() for error in result.errors)
    
    def test_validate_empty_edge_collection(self, validator, valid_template):
        """Test validation fails with empty edge collection name."""
        valid_template.config.edge_collections = ["follows", ""]
        result = validator.validate(valid_template)
        
        assert result.is_valid is False
        assert any("edge collection" in error.lower() for error in result.errors)
    
    def test_validate_edge_collection_with_spaces(self, validator, valid_template):
        """Test validation fails with spaces in edge collection name."""
        valid_template.config.edge_collections = ["has followed"]
        result = validator.validate(valid_template)
        
        assert result.is_valid is False
        assert any("edge collection" in error.lower() for error in result.errors)
    
    def test_validate_store_results_without_collection_warning(self, validator, valid_template):
        """Test validation warns when storing results without collection name."""
        valid_template.config.store_results = True
        valid_template.config.result_collection = None
        result = validator.validate(valid_template)
        
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert any("result" in warning.lower() for warning in result.warnings)
    
    def test_strict_mode_converts_warnings_to_errors(self, strict_validator, valid_template):
        """Test that strict mode converts warnings to errors."""
        valid_template.description = ""  # Would normally be a warning
        result = strict_validator.validate(valid_template)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert len(result.warnings) == 0
        assert any("warning" in error.lower() or "description" in error.lower() for error in result.errors)
    
    def test_validate_batch_all_valid(self, validator, valid_template):
        """Test batch validation with all valid templates."""
        templates = [valid_template] * 3
        
        valid, invalid = validator.validate_batch(templates)
        
        assert len(valid) == 3
        assert len(invalid) == 0
    
    def test_validate_batch_all_invalid(self, validator, valid_template):
        """Test batch validation with all invalid templates."""
        valid_template.name = ""  # Invalid
        templates = [valid_template] * 3
        
        valid, invalid = validator.validate_batch(templates)
        
        assert len(valid) == 0
        assert len(invalid) == 3
        
        # Check that results are included
        for template, result in invalid:
            assert isinstance(result, ValidationResult)
            assert not result.is_valid
    
    def test_validate_batch_mixed(self, validator, valid_template):
        """Test batch validation with mixed valid/invalid templates."""
        invalid_template = AnalysisTemplate(
            name="",  # Invalid
            description="Test",
            algorithm=AlgorithmParameters(algorithm=AlgorithmType.PAGERANK),
            config=TemplateConfig(graph_name="test")
        )
        
        templates = [valid_template, invalid_template, valid_template]
        
        valid, invalid = validator.validate_batch(templates)
        
        assert len(valid) == 2
        assert len(invalid) == 1
    
    def test_validate_different_algorithms(self, validator):
        """Test validation works for all algorithm types."""
        for algo_type in AlgorithmType:
            algorithm = AlgorithmParameters(algorithm=algo_type)
            config = TemplateConfig(graph_name="test_graph")
            
            template = AnalysisTemplate(
                name=f"Test {algo_type.value}",
                description="Test",
                algorithm=algorithm,
                config=config
            )
            
            result = validator.validate(template)
            
            # Should be valid (no specific params to validate)
            assert result.is_valid is True


class TestValidateTemplateFunction:
    """Tests for validate_template convenience function."""
    
    @pytest.fixture
    def valid_template(self):
        """Create a valid template."""
        algorithm = AlgorithmParameters(
            algorithm=AlgorithmType.PAGERANK,
            parameters={"damping_factor": 0.85}
        )
        config = TemplateConfig(graph_name="test_graph")
        
        return AnalysisTemplate(
            name="Test Template",
            description="Test",
            algorithm=algorithm,
            config=config
        )
    
    def test_validate_template_basic(self, valid_template):
        """Test basic template validation."""
        result = validate_template(valid_template)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
    
    def test_validate_template_strict_mode(self, valid_template):
        """Test template validation in strict mode."""
        valid_template.description = ""  # Would be warning in normal mode
        
        # Normal mode
        result_normal = validate_template(valid_template, strict=False)
        assert result_normal.is_valid is True
        
        # Strict mode
        result_strict = validate_template(valid_template, strict=True)
        assert result_strict.is_valid is False
    
    def test_validate_template_invalid(self, valid_template):
        """Test validation of invalid template."""
        valid_template.name = ""
        
        result = validate_template(valid_template)
        
        assert result.is_valid is False
        assert len(result.errors) > 0

