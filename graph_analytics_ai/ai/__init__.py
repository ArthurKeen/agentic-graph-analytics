"""
AI-assisted workflow module for Graph Analytics AI.

This module provides AI-powered features for automating graph analytics workflows:
- Graph schema extraction and analysis
- Automated PRD generation from business requirements
- Use case generation based on graph schema
- Analysis template generation
- Actionable intelligence reporting

All AI features are OPTIONAL and require explicit opt-in. The core library
works perfectly fine without this module.

Example - Schema Analysis:
    >>> from graph_analytics_ai.ai import create_llm_provider
    >>> from graph_analytics_ai.ai.schema import create_extractor, SchemaAnalyzer
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
    >>> print(analysis.description)
    >>> print(f"Suggested analyses: {len(analysis.suggested_analyses)}")

Example - Direct LLM Use:
    >>> from graph_analytics_ai.ai import create_llm_provider
    >>>
    >>> # Create LLM provider
    >>> provider = create_llm_provider(
    ...     provider="openrouter",
    ...     model="google/gemini-2.5-flash"
    ... )
    >>>
    >>> # Use for generation
    >>> response = provider.generate("What is graph analytics?")
    >>> print(response.content)

Note:
    AI features require:
    - LLM API key (OpenRouter, OpenAI, or Anthropic)
    - AI_WORKFLOW_ENABLED=true in environment (optional)
    - Additional dependencies: pip install graph-analytics-ai[ai]
"""

# LLM providers
from .llm import (
    LLMProvider,
    LLMConfig,
    LLMResponse,
    LLMProviderError,
    create_llm_provider,
    get_default_provider,
)

# Schema analysis / documents / generation / workflow (import submodules for convenience)
from . import schema
from . import documents
from . import generation
from . import workflow

__version__ = "3.0.0"  # AI module version (v3.0 = Phase 10 complete - All features)

__all__ = [
    # LLM providers
    "LLMProvider",
    "LLMConfig",
    "LLMResponse",
    "LLMProviderError",
    "create_llm_provider",
    "get_default_provider",
    # Submodules
    "schema",
    "documents",
    "generation",
    "workflow",
]
