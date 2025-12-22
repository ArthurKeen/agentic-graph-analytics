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
]
