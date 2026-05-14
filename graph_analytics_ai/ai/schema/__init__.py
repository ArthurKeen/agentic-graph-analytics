"""
Graph schema extraction and analysis module.

This module provides tools for extracting schema information from ArangoDB
databases and analyzing it using LLMs to generate insights.

Example:
    >>> from graph_analytics_ai.ai.schema import create_extractor, SchemaAnalyzer
    >>> from graph_analytics_ai.ai.llm import create_llm_provider
    >>>
    >>> # Extract schema from database
    >>> extractor = create_extractor(
    ...     endpoint='http://localhost:8529',
    ...     database='my_graph',
    ...     password='password'
    ... )
    >>> schema = extractor.extract()
    >>>
    >>> # Analyze with LLM
    >>> provider = create_llm_provider()
    >>> analyzer = SchemaAnalyzer(provider)
    >>> analysis = analyzer.analyze(schema)
    >>>
    >>> # Generate report
    >>> report = analyzer.generate_report(analysis)
    >>> print(report)
"""

from .models import (
    GraphSchema,
    CollectionSchema,
    CollectionType,
    AttributeInfo,
    Relationship,
    SchemaAnalysis,
)

from .extractor import SchemaExtractor, create_extractor

from .analyzer import SchemaAnalyzer

# Phase 6a (PRD v0.6 / FR-56..FR-60): three-tier acquisition.
from .acquire import (
    DETECTED_PATTERN_TAGS,
    InMemorySchemaCache,
    SchemaAcquisitionBundle,
    SchemaCache,
    SchemaChangeReport,
    SchemaKind,
    SchemaStrategy,
    acquire_schema,
    build_heuristic_bundle,
    cache_key,
    describe_schema_change,
    invalidate_schema_cache,
    reset_default_cache,
)
# Phase 6b (PRD v0.6 / FR-61..FR-63): graph-purpose classifier.
from .graph_purpose import (
    GraphPurpose,
    GraphPurposeResult,
    classify_graph_purpose,
)
# Phase 6d (PRD v0.6 / FR-72): sensitivity classifier.
from .sensitivity import (
    PropertySensitivity,
    SensitivityLevel,
    SensitivityReport,
    classify_conceptual_schema,
    classify_property_sensitivity,
    classify_schema_sensitivity,
)
# v0.6.1 / Phase 6e (FR-73 candidate): first-party Arango product
# detection (Autograph corpus + KG today). The ``arango_products``
# module is a shim that prefers the upstream detector in
# ``schema_analyzer.arango_products`` and falls back to the in-tree
# ``_arango_products_local`` implementation when the analyzer is
# unavailable. Importers should always go through this re-export.
from .arango_products import (
    ArangoProductReport,
    AutographProject,
    detect_arango_products,
)


__all__ = [
    # Models
    "GraphSchema",
    "CollectionSchema",
    "CollectionType",
    "AttributeInfo",
    "Relationship",
    "SchemaAnalysis",
    # Extractor
    "SchemaExtractor",
    "create_extractor",
    # Analyzer
    "SchemaAnalyzer",
    # Acquisition (v0.6)
    "DETECTED_PATTERN_TAGS",
    "InMemorySchemaCache",
    "SchemaAcquisitionBundle",
    "SchemaCache",
    "SchemaChangeReport",
    "SchemaKind",
    "SchemaStrategy",
    "acquire_schema",
    "build_heuristic_bundle",
    "cache_key",
    "describe_schema_change",
    "invalidate_schema_cache",
    "reset_default_cache",
    # v0.6 / Phase 6b
    "GraphPurpose",
    "GraphPurposeResult",
    "classify_graph_purpose",
    # v0.6 / Phase 6d
    "PropertySensitivity",
    "SensitivityLevel",
    "SensitivityReport",
    "classify_conceptual_schema",
    "classify_property_sensitivity",
    "classify_schema_sensitivity",
    # v0.6.1 / Phase 6e
    "ArangoProductReport",
    "AutographProject",
    "detect_arango_products",
]
