"""
LLM provider base interface for AI-assisted workflows.

This module provides the abstract base class for all LLM providers,
ensuring a consistent interface regardless of the underlying provider
(OpenRouter, OpenAI, Anthropic, etc.).
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from LLM provider."""

    content: str
    """Generated text content."""

    prompt_tokens: int = 0
    """Number of tokens in the prompt."""

    completion_tokens: int = 0
    """Number of tokens in the completion."""

    total_tokens: int = 0
    """Total tokens used (prompt + completion)."""

    model: Optional[str] = None
    """Model used for generation."""

    metadata: Optional[Dict[str, Any]] = None
    """Additional provider-specific metadata."""

    @property
    def cost_usd(self) -> float:
        """Estimated cost in USD (if available in metadata)."""
        if self.metadata and "cost_usd" in self.metadata:
            return self.metadata["cost_usd"]
        return 0.0


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    api_key: str
    """API key for the provider."""

    model: str
    """Model name to use."""

    max_tokens: int = 4000
    """Maximum tokens to generate."""

    temperature: float = 0.7
    """Sampling temperature (0.0 = deterministic, 1.0 = creative)."""

    timeout: int = 60
    """Request timeout in seconds."""

    max_retries: int = 3
    """Maximum number of retries on failure."""

    base_url: Optional[str] = None
    """Custom base URL (for custom/self-hosted providers)."""


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""

    pass


class LLMRateLimitError(LLMProviderError):
    """Raised when rate limit is exceeded."""

    pass


class LLMAuthenticationError(LLMProviderError):
    """Raised when authentication fails."""

    pass


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM providers (OpenRouter, OpenAI, Anthropic, etc.) must implement
    this interface to ensure consistent behavior across the application.

    Example:
        >>> provider = OpenRouterProvider(
        ...     api_key="sk-...",
        ...     model="google/gemini-2.5-flash"
        ... )
        >>> response = provider.generate("What is the capital of France?")
        >>> print(response.content)
        "Paris is the capital of France."
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize the LLM provider.

        Args:
            config: LLM configuration.
        """
        self.config = config

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Generate text from a prompt.

        Args:
            prompt: The prompt to generate from.
            **kwargs: Additional generation parameters.

        Returns:
            LLMResponse containing generated text and metadata.

        Raises:
            LLMProviderError: If generation fails.
            LLMRateLimitError: If rate limit is exceeded.
            LLMAuthenticationError: If authentication fails.
        """
        pass

    @abstractmethod
    def generate_structured(
        self, prompt: str, schema: Dict[str, Any], **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured output matching a schema.

        Args:
            prompt: The prompt to generate from.
            schema: JSON schema for the expected output structure.
            **kwargs: Additional generation parameters.

        Returns:
            Dictionary matching the provided schema.

        Raises:
            LLMProviderError: If generation fails.
            ValueError: If response doesn't match schema.
        """
        pass

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """
        Generate response from a conversation history.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
                      Example: [{"role": "user", "content": "Hello!"}]
            **kwargs: Additional generation parameters.

        Returns:
            LLMResponse containing generated response and metadata.

        Raises:
            LLMProviderError: If generation fails.
        """
        pass

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimate cost for given token counts.

        Args:
            prompt_tokens: Number of input tokens.
            completion_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD.

        Note:
            Default implementation returns 0.0. Providers should override
            with their specific pricing models.
        """
        return 0.0

    @property
    def name(self) -> str:
        """Provider name (e.g., 'openrouter', 'openai')."""
        return self.__class__.__name__.lower().replace("provider", "")

    @property
    def model_name(self) -> str:
        """Model name being used."""
        return self.config.model
