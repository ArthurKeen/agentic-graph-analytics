"""
GAE Template Generation Module

Generates ArangoDB Graph Analytics Engine (GAE) AnalysisConfig templates from use cases.
Converts high-level use case descriptions into executable GAE job configurations.
"""

from .generator import TemplateGenerator, generate_template
from .models import (
    AnalysisTemplate,
    AlgorithmType,
    EngineSize,
    TemplateConfig,
    AlgorithmParameters,
    DEFAULT_ALGORITHM_PARAMS,
    recommend_engine_size,
)
from .validator import TemplateValidator, ValidationResult, validate_template
from .collection_selector import (
    CollectionSelector,
    CollectionSelection,
    CollectionRole,
    select_collections_for_algorithm,
)

__all__ = [
    "TemplateGenerator",
    "generate_template",
    "AnalysisTemplate",
    "AlgorithmType",
    "EngineSize",
    "TemplateConfig",
    "AlgorithmParameters",
    "DEFAULT_ALGORITHM_PARAMS",
    "recommend_engine_size",
    "TemplateValidator",
    "ValidationResult",
    "validate_template",
    "CollectionSelector",
    "CollectionSelection",
    "CollectionRole",
    "select_collections_for_algorithm",
]
