"""
LLM provider factory for creating provider instances.

This module provides a factory function to create the appropriate
LLM provider based on configuration.
"""

import os
from typing import Optional

from .base import LLMProvider, LLMConfig, LLMProviderError
from .openrouter import OpenRouterProvider


def create_llm_provider(
    provider: str = "openrouter",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs,
) -> LLMProvider:
    """
    Create an LLM provider instance.

    Args:
        provider: Provider name ('openrouter', 'openai', 'anthropic').
        api_key: API key for the provider. If None, reads from environment.
        model: Model name to use. If None, reads from environment or uses default.
        **kwargs: Additional configuration parameters.

    Returns:
        Configured LLM provider instance.

    Raises:
        LLMProviderError: If provider is not supported or configuration is invalid.

    Example:
        >>> # Using environment variables
        >>> provider = create_llm_provider()
        >>>
        >>> # Or specify explicitly
        >>> provider = create_llm_provider(
        ...     provider="openrouter",
        ...     api_key="sk-or-v1-...",
        ...     model="google/gemini-2.5-flash"
        ... )
        >>>
        >>> response = provider.generate("Hello!")
    """
    # Get configuration from environment if not provided
    if api_key is None:
        api_key = _get_api_key_from_env(provider)

    if model is None:
        model = _get_model_from_env(provider)

    if not api_key:
        raise LLMProviderError(
            f"No API key provided for {provider}. "
            f"Set {provider.upper()}_API_KEY environment variable or pass api_key parameter."
        )

    if not model:
        raise LLMProviderError(
            f"No model specified for {provider}. "
            f"Set {provider.upper()}_MODEL environment variable or pass model parameter."
        )

    # Create configuration
    config = LLMConfig(
        api_key=api_key,
        model=model,
        max_tokens=kwargs.get("max_tokens", int(os.getenv("LLM_MAX_TOKENS", "4000"))),
        temperature=kwargs.get(
            "temperature", float(os.getenv("LLM_TEMPERATURE", "0.7"))
        ),
        timeout=kwargs.get("timeout", int(os.getenv("LLM_TIMEOUT", "60"))),
        max_retries=kwargs.get("max_retries", int(os.getenv("LLM_MAX_RETRIES", "3"))),
        base_url=kwargs.get("base_url"),
    )

    # Create provider instance
    provider = provider.lower()

    if provider == "openrouter":
        return OpenRouterProvider(config)

    elif provider == "openai":
        # Import here to avoid requiring openai package if not used
        try:
            from .openai import OpenAIProvider

            return OpenAIProvider(config)
        except ImportError:
            raise LLMProviderError(
                "OpenAI provider requires 'openai' package. "
                "Install with: pip install openai"
            )

    elif provider == "anthropic":
        # Import here to avoid requiring anthropic package if not used
        try:
            from .anthropic import AnthropicProvider

            return AnthropicProvider(config)
        except ImportError:
            raise LLMProviderError(
                "Anthropic provider requires 'anthropic' package. "
                "Install with: pip install anthropic"
            )

    else:
        raise LLMProviderError(
            f"Unsupported provider: {provider}. "
            f"Supported providers: openrouter, openai, anthropic"
        )


def _get_api_key_from_env(provider: str) -> Optional[str]:
    """Get API key from environment variables."""
    provider = provider.upper()

    # Try provider-specific key first
    key = os.getenv(f"{provider}_API_KEY")
    if key:
        return key

    # Fall back to generic LLM_API_KEY
    return os.getenv("LLM_API_KEY")


def _get_model_from_env(provider: str) -> Optional[str]:
    """Get model name from environment variables."""
    provider = provider.upper()

    # Try provider-specific model first
    model = os.getenv(f"{provider}_MODEL")
    if model:
        return model

    # Fall back to generic LLM_MODEL
    model = os.getenv("LLM_MODEL")
    if model:
        return model

    # Return default models by provider
    defaults = {
        "OPENROUTER": "google/gemini-2.5-flash",
        "OPENAI": "gpt-4o",
        "ANTHROPIC": "claude-3-5-sonnet-20241022",
    }

    return defaults.get(provider)


def get_default_provider() -> LLMProvider:
    """
    Get default LLM provider based on environment configuration.

    Reads LLM_PROVIDER environment variable (defaults to 'openrouter')
    and creates provider with environment-based configuration.

    Returns:
        Configured LLM provider instance.

    Raises:
        LLMProviderError: If configuration is invalid.

    Example:
        >>> provider = get_default_provider()
        >>> response = provider.generate("Hello!")
    """
    provider_name = os.getenv("LLM_PROVIDER", "openrouter")
    return create_llm_provider(provider=provider_name)
