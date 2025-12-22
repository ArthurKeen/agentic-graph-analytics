"""
OpenRouter LLM provider implementation.

OpenRouter provides access to 100+ LLM models through a unified API.
https://openrouter.ai/
"""

import json
import time
import requests
from typing import Dict, List, Any

from .base import (
    LLMProvider,
    LLMConfig,
    LLMResponse,
    LLMProviderError,
    LLMRateLimitError,
    LLMAuthenticationError,
)


# OpenRouter pricing per 1M tokens (approximate, as of Dec 2025)
OPENROUTER_PRICING = {
    "google/gemini-2.0-flash-001:free": {"input": 0, "output": 0},
    "google/gemini-2.5-flash": {"input": 0.10, "output": 0.10},
    "google/gemini-pro": {"input": 0.50, "output": 1.50},
    "anthropic/claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    "openai/gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}


class OpenRouterProvider(LLMProvider):
    """
    OpenRouter LLM provider.

    Provides access to multiple LLM providers through OpenRouter's unified API.

    Example:
        >>> from graph_analytics_ai.ai.llm import OpenRouterProvider, LLMConfig
        >>>
        >>> config = LLMConfig(
        ...     api_key="sk-or-v1-...",
        ...     model="google/gemini-2.5-flash",
        ...     max_tokens=4000,
        ...     temperature=0.7
        ... )
        >>> provider = OpenRouterProvider(config)
        >>>
        >>> response = provider.generate("What is graph analytics?")
        >>> print(response.content)
        >>> print(f"Cost: ${response.cost_usd:.4f}")
    """

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, config: LLMConfig):
        """
        Initialize OpenRouter provider.

        Args:
            config: LLM configuration with OpenRouter API key.
        """
        super().__init__(config)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {config.api_key}",
                "HTTP-Referer": "https://github.com/ArthurKeen/graph-analytics-ai",
                "X-Title": "Graph Analytics AI",
            }
        )

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate text from a prompt using OpenRouter."""
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, **kwargs)

    def generate_structured(
        self, prompt: str, schema: Dict[str, Any], **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured output matching a schema.

        Instructs the LLM to return JSON matching the provided schema.
        """
        # Enhance prompt with schema instructions
        schema_str = json.dumps(schema, indent=2)
        enhanced_prompt = f"""{prompt}

Please respond with valid JSON matching this schema:
{schema_str}

Return only the JSON, no additional text."""

        response = self.generate(enhanced_prompt, **kwargs)

        # Parse JSON from response
        try:
            # Try to extract JSON if wrapped in markdown
            content = response.content.strip()
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)
            return result
        except json.JSONDecodeError as e:
            raise LLMProviderError(
                f"Failed to parse JSON from LLM response: {e}\n"
                f"Response: {response.content[:500]}"
            )

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """Generate response from conversation history."""
        # Merge kwargs with config
        params = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }

        # Make request with retry logic
        for attempt in range(self.config.max_retries):
            try:
                response = self._make_request(params)
                return self._parse_response(response)

            except LLMRateLimitError:
                if attempt < self.config.max_retries - 1:
                    # Exponential backoff
                    wait_time = 2**attempt
                    time.sleep(wait_time)
                    continue
                raise

            except LLMAuthenticationError:
                # Don't retry auth errors
                raise

            except LLMProviderError:
                if attempt < self.config.max_retries - 1:
                    time.sleep(1)
                    continue
                raise

        raise LLMProviderError(f"Failed after {self.config.max_retries} attempts")

    def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to OpenRouter API."""
        url = f"{self.BASE_URL}/chat/completions"

        try:
            response = self.session.post(url, json=params, timeout=self.config.timeout)

            # Handle different error codes
            if response.status_code == 401:
                raise LLMAuthenticationError(
                    "Invalid API key. Please check your OPENROUTER_API_KEY."
                )

            elif response.status_code == 429:
                raise LLMRateLimitError("Rate limit exceeded. Please try again later.")

            elif response.status_code >= 400:
                error_msg = f"API error {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg += f": {error_data['error']}"
                except:
                    error_msg += f": {response.text[:200]}"

                raise LLMProviderError(error_msg)

            return response.json()

        except requests.exceptions.Timeout:
            raise LLMProviderError(
                f"Request timed out after {self.config.timeout} seconds"
            )

        except requests.exceptions.RequestException as e:
            raise LLMProviderError(f"Request failed: {e}")

    def _parse_response(self, response_data: Dict[str, Any]) -> LLMResponse:
        """Parse OpenRouter API response."""
        try:
            choice = response_data["choices"][0]
            content = choice["message"]["content"]

            usage = response_data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)

            # Calculate cost
            cost = self.estimate_cost(prompt_tokens, completion_tokens)

            return LLMResponse(
                content=content,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                model=response_data.get("model", self.config.model),
                metadata={
                    "cost_usd": cost,
                    "finish_reason": choice.get("finish_reason"),
                    "id": response_data.get("id"),
                },
            )

        except (KeyError, IndexError) as e:
            raise LLMProviderError(
                f"Unexpected response format: {e}\n"
                f"Response: {json.dumps(response_data)[:500]}"
            )

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimate cost for given token counts using OpenRouter pricing.

        Returns cost in USD.
        """
        model = self.config.model

        # Get pricing for model (default to unknown if not found)
        pricing = OPENROUTER_PRICING.get(model, {"input": 0, "output": 0})

        # Calculate cost (pricing is per 1M tokens)
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    @property
    def name(self) -> str:
        """Provider name."""
        return "openrouter"
