"""
Template validation utilities.

Validates GAE analysis templates before execution.
"""

from typing import List, Tuple
from dataclasses import dataclass

from .models import AnalysisTemplate, AlgorithmType, EngineSize


@dataclass
class ValidationResult:
    """Result of template validation."""

    is_valid: bool
    """Whether the template is valid."""

    errors: List[str]
    """List of validation errors."""

    warnings: List[str]
    """List of validation warnings."""

    def __bool__(self) -> bool:
        """Allow truth testing."""
        return self.is_valid


class TemplateValidator:
    """
    Validates GAE analysis templates.

    Checks for:
    - Required fields
    - Valid algorithm parameters
    - Reasonable engine sizes
    - Valid collection names

    Example:
        >>> from graph_analytics_ai.ai.templates import TemplateValidator
        >>>
        >>> validator = TemplateValidator()
        >>> result = validator.validate(template)
        >>>
        >>> if not result:
        ...     print("Errors:", result.errors)
        >>> if result.warnings:
        ...     print("Warnings:", result.warnings)
    """

    def __init__(self, strict: bool = False):
        """
        Initialize validator.

        Args:
            strict: If True, warnings become errors
        """
        self.strict = strict

    def validate(self, template: AnalysisTemplate) -> ValidationResult:
        """
        Validate a template.

        Args:
            template: Template to validate

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Check name
        if not template.name or not template.name.strip():
            errors.append("Template name is required")
        elif len(template.name) > 200:
            warnings.append(f"Template name is very long ({len(template.name)} chars)")

        # Check description
        if not template.description or not template.description.strip():
            warnings.append("Template description is empty")

        # Validate algorithm
        algo_errors, algo_warnings = self._validate_algorithm(template)
        errors.extend(algo_errors)
        warnings.extend(algo_warnings)

        # Validate config
        config_errors, config_warnings = self._validate_config(template)
        errors.extend(config_errors)
        warnings.extend(config_warnings)

        # Check runtime estimate
        if template.estimated_runtime_seconds is not None:
            if template.estimated_runtime_seconds < 0:
                errors.append("Estimated runtime cannot be negative")
            elif template.estimated_runtime_seconds > 3600:  # 1 hour
                warnings.append(
                    f"Very long estimated runtime: {template.estimated_runtime_seconds}s"
                )

        # Convert warnings to errors in strict mode
        if self.strict and warnings:
            errors.extend([f"Warning (strict): {w}" for w in warnings])
            warnings = []

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def validate_batch(
        self, templates: List[AnalysisTemplate]
    ) -> Tuple[List[AnalysisTemplate], List[Tuple[AnalysisTemplate, ValidationResult]]]:
        """
        Validate multiple templates.

        Args:
            templates: Templates to validate

        Returns:
            Tuple of (valid_templates, invalid_with_results)
        """
        valid = []
        invalid = []

        for template in templates:
            result = self.validate(template)
            if result.is_valid:
                valid.append(template)
            else:
                invalid.append((template, result))

        return valid, invalid

    def _validate_algorithm(
        self, template: AnalysisTemplate
    ) -> Tuple[List[str], List[str]]:
        """Validate algorithm configuration."""
        errors = []
        warnings = []

        algo = template.algorithm
        algo_type = algo.algorithm
        params = algo.parameters

        # Algorithm-specific validation for supported GAE algorithms
        if algo_type == AlgorithmType.PAGERANK:
            # Check damping factor
            if "damping_factor" in params:
                df = params["damping_factor"]
                if not (0 < df < 1):
                    errors.append(
                        f"PageRank damping_factor must be between 0 and 1, got {df}"
                    )

            # Check maximum supersteps
            if "maximum_supersteps" in params:
                ms = params["maximum_supersteps"]
                if ms < 1:
                    errors.append(
                        f"PageRank maximum_supersteps must be positive, got {ms}"
                    )
                elif ms > 500:
                    warnings.append(f"PageRank maximum_supersteps is very high: {ms}")

        elif algo_type == AlgorithmType.LABEL_PROPAGATION:
            # Check maximum supersteps
            if "maximum_supersteps" in params:
                ms = params["maximum_supersteps"]
                if ms < 1:
                    errors.append(
                        f"Label Propagation maximum_supersteps must be positive, got {ms}"
                    )
                elif ms > 500:
                    warnings.append(
                        f"Label Propagation maximum_supersteps is very high: {ms}"
                    )

            # Check start_label_attribute
            if "start_label_attribute" in params:
                attr = params["start_label_attribute"]
                if not isinstance(attr, str) or not attr.strip():
                    errors.append("start_label_attribute must be a non-empty string")

        elif algo_type == AlgorithmType.BETWEENNESS_CENTRALITY:
            # Check maximum supersteps
            if "maximum_supersteps" in params:
                ms = params["maximum_supersteps"]
                if ms < 1:
                    errors.append(
                        f"Betweenness Centrality maximum_supersteps must be positive, got {ms}"
                    )
                elif ms > 500:
                    warnings.append(
                        f"Betweenness Centrality maximum_supersteps is very high: {ms}"
                    )

        elif algo_type in (AlgorithmType.WCC, AlgorithmType.SCC):
            # WCC and SCC have no parameters - but warn if unexpected params provided
            if params and any(k not in ["graph_id"] for k in params.keys()):
                warnings.append(
                    f"{algo_type.value.upper()} algorithm has no parameters, ignoring: {list(params.keys())}"
                )

        return errors, warnings

    def _validate_config(
        self, template: AnalysisTemplate
    ) -> Tuple[List[str], List[str]]:
        """Validate template configuration."""
        errors = []
        warnings = []

        config = template.config

        # Check graph name
        if not config.graph_name or not config.graph_name.strip():
            errors.append("Graph name is required")

        # Check engine size
        if config.engine_size not in list(EngineSize):
            errors.append(f"Invalid engine size: {config.engine_size}")

        # Check result collection
        if config.store_results and not config.result_collection:
            warnings.append("store_results is True but no result_collection specified")

        # Check collection names (basic validation)
        for coll in config.vertex_collections:
            if not coll or not coll.strip():
                errors.append("Empty vertex collection name")
            elif " " in coll:
                errors.append(
                    f"Invalid vertex collection name: '{coll}' (contains spaces)"
                )

        for coll in config.edge_collections:
            if not coll or not coll.strip():
                errors.append("Empty edge collection name")
            elif " " in coll:
                errors.append(
                    f"Invalid edge collection name: '{coll}' (contains spaces)"
                )

        return errors, warnings


def validate_template(
    template: AnalysisTemplate, strict: bool = False
) -> ValidationResult:
    """
    Convenience function to validate a single template.

    Args:
        template: Template to validate
        strict: If True, warnings become errors

    Returns:
        ValidationResult
    """
    validator = TemplateValidator(strict=strict)
    return validator.validate(template)
