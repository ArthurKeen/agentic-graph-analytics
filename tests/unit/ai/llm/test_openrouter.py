"""
Unit tests for OpenRouter LLM provider.

Tests the OpenRouter provider implementation with mocked HTTP responses.
"""

import pytest
import responses

from graph_analytics_ai.ai.llm import (
    OpenRouterProvider,
    LLMConfig,
    LLMRateLimitError,
    LLMAuthenticationError,
)


@pytest.fixture
def llm_config():
    """Create test LLM configuration."""
    return LLMConfig(
        api_key="test-api-key",
        model="google/gemini-2.5-flash",
        max_tokens=1000,
        temperature=0.7,
    )


@pytest.fixture
def provider(llm_config):
    """Create OpenRouter provider instance."""
    return OpenRouterProvider(llm_config)


class TestOpenRouterProvider:
    """Test OpenRouter provider implementation."""

    @responses.activate
    def test_generate_success(self, provider):
        """Test successful text generation."""
        # Arrange
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "choices": [
                    {
                        "message": {"content": "This is a generated response."},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                },
                "model": "google/gemini-2.5-flash",
                "id": "test-id-123",
            },
            status=200,
        )

        # Act
        response = provider.generate("Test prompt")

        # Assert
        assert response.content == "This is a generated response."
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 20
        assert response.total_tokens == 30
        assert response.model == "google/gemini-2.5-flash"
        assert "cost_usd" in response.metadata

        # Verify request
        assert len(responses.calls) == 1
        request = responses.calls[0].request
        assert request.headers["Authorization"] == "Bearer test-api-key"

    @responses.activate
    def test_generate_structured_success(self, provider):
        """Test successful structured generation."""
        # Arrange
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"summary": "Test summary", "confidence": 0.95}'
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                },
            },
            status=200,
        )

        schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "confidence": {"type": "number"},
            },
        }

        # Act
        result = provider.generate_structured("Analyze this", schema)

        # Assert
        assert result["summary"] == "Test summary"
        assert result["confidence"] == 0.95

    @responses.activate
    def test_generate_structured_with_markdown_json(self, provider):
        """Test parsing JSON wrapped in markdown code blocks."""
        # Arrange
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "choices": [
                    {"message": {"content": '```json\n{"result": "success"}\n```'}}
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 10,
                    "total_tokens": 20,
                },
            },
            status=200,
        )

        # Act
        result = provider.generate_structured("Test", {})

        # Assert
        assert result["result"] == "success"

    @responses.activate
    def test_authentication_error(self, provider):
        """Test handling of authentication errors."""
        # Arrange
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={"error": "Invalid API key"},
            status=401,
        )

        # Act & Assert
        with pytest.raises(LLMAuthenticationError) as exc_info:
            provider.generate("Test prompt")

        assert "Invalid API key" in str(exc_info.value)

    @responses.activate
    def test_rate_limit_error(self, provider):
        """Test handling of rate limit errors."""
        # Arrange
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={"error": "Rate limit exceeded"},
            status=429,
        )

        # Act & Assert
        with pytest.raises(LLMRateLimitError) as exc_info:
            provider.generate("Test prompt")

        assert "Rate limit exceeded" in str(exc_info.value)

    @responses.activate
    def test_retry_on_rate_limit(self, provider, mocker):
        """Test that provider retries on rate limit."""
        # Arrange
        mock_sleep = mocker.patch("time.sleep")

        # First two requests fail with rate limit, third succeeds
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={"error": "Rate limit"},
            status=429,
        )
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={"error": "Rate limit"},
            status=429,
        )
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "choices": [{"message": {"content": "Success"}}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 10,
                    "total_tokens": 20,
                },
            },
            status=200,
        )

        # Act
        response = provider.generate("Test")

        # Assert
        assert response.content == "Success"
        assert len(responses.calls) == 3
        assert mock_sleep.call_count == 2  # Slept between retries

    @responses.activate
    def test_chat_with_message_history(self, provider):
        """Test chat method with message history."""
        # Arrange
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "choices": [{"message": {"content": "Hello! How can I help you?"}}],
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 10,
                    "total_tokens": 30,
                },
            },
            status=200,
        )

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]

        # Act
        response = provider.chat(messages)

        # Assert
        assert response.content == "Hello! How can I help you?"
        assert response.prompt_tokens == 20

    def test_estimate_cost(self, provider):
        """Test cost estimation for known models."""
        # Act
        cost = provider.estimate_cost(
            prompt_tokens=1_000_000,  # 1M tokens
            completion_tokens=1_000_000,  # 1M tokens
        )

        # Assert
        # google/gemini-2.5-flash: $0.10 per 1M tokens (both input/output)
        assert cost == pytest.approx(0.20, rel=0.01)

    def test_provider_name(self, provider):
        """Test provider name property."""
        assert provider.name == "openrouter"

    def test_model_name(self, provider):
        """Test model name property."""
        assert provider.model_name == "google/gemini-2.5-flash"


class TestLLMResponse:
    """Test LLMResponse dataclass."""

    def test_cost_usd_from_metadata(self):
        """Test extracting cost from metadata."""
        from graph_analytics_ai.ai.llm.base import LLMResponse

        response = LLMResponse(content="test", metadata={"cost_usd": 0.05})

        assert response.cost_usd == 0.05

    def test_cost_usd_default(self):
        """Test default cost when not in metadata."""
        from graph_analytics_ai.ai.llm.base import LLMResponse

        response = LLMResponse(content="test")

        assert response.cost_usd == 0.0
