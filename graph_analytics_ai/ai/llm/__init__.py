"""
LLM (Large Language Model) provider abstraction layer.

This module provides a unified interface for working with different LLM providers
(OpenRouter, OpenAI, Anthropic, etc.) through a common API.

Example:
    >>> from graph_analytics_ai.ai.llm import create_llm_provider
    >>>
    >>> # Create provider (reads from environment)
    >>> provider = create_llm_provider()
    >>>
    >>> # Generate text
    >>> response = provider.generate("What is graph analytics?")
    >>> print(response.content)
    >>> print(f"Cost: ${response.cost_usd:.4f}")
    >>>
    >>> # Generate structured output
    >>> schema = {
    ...     "type": "object",
    ...     "properties": {
    ...         "summary": {"type": "string"},
    ...         "confidence": {"type": "number"}
    ...     }
    ... }
    >>> result = provider.generate_structured("Analyze this...", schema)
    >>> print(result["summary"])
"""

from .base import (
    LLMProvider,
    LLMConfig,
    LLMResponse,
    LLMProviderError,
    LLMRateLimitError,
    LLMAuthenticationError,
)

from .factory import create_llm_provider, get_default_provider

from .openrouter import OpenRouterProvider


__all__ = [
    # Base classes
    "LLMProvider",
    "LLMConfig",
    "LLMResponse",
    # Exceptions
    "LLMProviderError",
    "LLMRateLimitError",
    "LLMAuthenticationError",
    # Factory functions
    "create_llm_provider",
    "get_default_provider",
    # Providers
    "OpenRouterProvider",
]
