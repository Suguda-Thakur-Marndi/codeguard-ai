"""Tests for LLM Provider abstraction, GeminiProvider error handling/retries, and MockLLMProvider."""

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from app.agents.llm.gemini import GeminiProvider
from app.agents.llm.mock import MockLLMProvider
from app.agents.llm.provider import (
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMValidationError,
    ModelTier,
)


class SampleOutput(BaseModel):
    name: str
    score: float
    items: list[str] = []


@pytest.mark.asyncio
async def test_mock_llm_provider_structured():
    """MockLLMProvider should return registered structured response with token tracking."""
    provider = MockLLMProvider()
    expected = SampleOutput(name="TestReview", score=0.95, items=["item1", "item2"])

    provider.register_structured_response(
        lambda prompt, schema: schema is SampleOutput,
        expected,
    )

    resp = await provider.generate_structured(
        prompt="Analyze code",
        response_schema=SampleOutput,
        model_tier=ModelTier.FAST,
    )

    assert resp.data == expected
    assert resp.model_name == "mock-fast"
    assert resp.token_usage.total_tokens == provider.fixed_input_tokens + provider.fixed_output_tokens
    assert resp.token_usage.estimated_cost > 0
    assert len(provider.call_history) == 1


@pytest.mark.asyncio
async def test_mock_llm_provider_transient_failure_and_recovery():
    """MockLLMProvider transient failure should raise specified times then succeed."""
    provider = MockLLMProvider()
    provider.set_transient_failure(LLMRateLimitError("Rate limit exceeded"), failures=2)

    with pytest.raises(LLMRateLimitError):
        await provider.generate_text("Prompt 1")

    with pytest.raises(LLMRateLimitError):
        await provider.generate_text("Prompt 2")

    # 3rd attempt succeeds
    resp = await provider.generate_text("Prompt 3")
    assert resp.data == "Mock text response"


@pytest.mark.asyncio
async def test_gemini_provider_cost_calculation():
    """GeminiProvider should correctly calculate token pricing based on model tier and usage."""
    provider = GeminiProvider(api_key="test-api-key")
    usage = provider.calculate_cost(input_tokens=1000, output_tokens=500, model_tier=ModelTier.REASONING)

    assert usage.input_tokens == 1000
    assert usage.output_tokens == 500
    assert usage.total_tokens == 1500
    # Reasoning pricing: 1.25 / 1M input, 5.00 / 1M output
    expected_cost = (1000 / 1_000_000 * 1.25) + (500 / 1_000_000 * 5.00)
    assert pytest.approx(usage.estimated_cost, rel=1e-5) == expected_cost


@pytest.mark.asyncio
async def test_gemini_provider_structured_success():
    """GeminiProvider generate_structured should call google-genai client and parse schema."""
    provider = GeminiProvider(api_key="test-key", max_retries=1)

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"name": "SecurityAudit", "score": 0.99, "items": ["sink", "source"]}'
    mock_response.usage_metadata = MagicMock(
        prompt_token_count=200, candidates_token_count=100, total_token_count=300
    )

    mock_client.models.generate_content = MagicMock(return_value=mock_response)
    provider._client = mock_client

    resp = await provider.generate_structured(
        prompt="Analyze vulnerable code",
        response_schema=SampleOutput,
        system_instruction="You are a security reviewer.",
        model_tier=ModelTier.REASONING,
    )

    assert resp.data.name == "SecurityAudit"
    assert resp.data.score == 0.99
    assert resp.data.items == ["sink", "source"]
    assert resp.token_usage.input_tokens == 200
    assert resp.token_usage.output_tokens == 100
    assert resp.token_usage.total_tokens == 300


@pytest.mark.asyncio
async def test_gemini_provider_rate_limit_retry_and_exhaustion():
    """GeminiProvider should retry on 429/ResourceExhausted and raise LLMRateLimitError on exhaustion."""
    provider = GeminiProvider(api_key="test-key", max_retries=2, retry_delay=0.001)

    mock_client = MagicMock()
    mock_client.models.generate_content = MagicMock(
        side_effect=Exception("429 Resource has been exhausted (e.g. check quota).")
    )
    provider._client = mock_client

    with pytest.raises(LLMRateLimitError) as exc_info:
        await provider.generate_text("test prompt")

    assert "rate limit" in str(exc_info.value).lower()
    # With max_retries=2: 1 initial call + 2 retries = 3 calls
    assert mock_client.models.generate_content.call_count == 3


@pytest.mark.asyncio
async def test_gemini_provider_timeout_retry():
    """GeminiProvider should retry on asyncio.TimeoutError."""
    provider = GeminiProvider(api_key="test-key", max_retries=2, retry_delay=0.001)

    mock_client = MagicMock()
    mock_client.models.generate_content = MagicMock(side_effect=TimeoutError("Request timed out"))
    provider._client = mock_client

    with pytest.raises(LLMTimeoutError):
        await provider.generate_text("test prompt")

    assert mock_client.models.generate_content.call_count == 3


@pytest.mark.asyncio
async def test_gemini_provider_auth_error_no_retry():
    """GeminiProvider should fail immediately without retrying on 401/403 or invalid API key."""
    provider = GeminiProvider(api_key="invalid-key", max_retries=3, retry_delay=0.001)

    mock_client = MagicMock()
    mock_client.models.generate_content = MagicMock(side_effect=Exception("401 Unauthorized API key not valid"))
    provider._client = mock_client

    with pytest.raises(LLMAuthenticationError):
        await provider.generate_text("test prompt")

    # Only 1 call made, zero retries!
    assert mock_client.models.generate_content.call_count == 1


@pytest.mark.asyncio
async def test_gemini_provider_validation_error_on_malformed_json():
    """GeminiProvider should raise LLMValidationError when response fails JSON / Pydantic validation."""
    provider = GeminiProvider(api_key="test-key", max_retries=1, retry_delay=0.001)

    mock_client = MagicMock()
    mock_response = MagicMock()
    # Missing required 'name' and 'score'
    mock_response.text = '{"unknown_field": 123}'
    mock_response.usage_metadata = MagicMock(prompt_token_count=50, candidates_token_count=10)

    mock_client.models.generate_content = MagicMock(return_value=mock_response)
    provider._client = mock_client

    with pytest.raises(LLMValidationError):
        await provider.generate_structured(
            prompt="Analyze code",
            response_schema=SampleOutput,
            model_tier=ModelTier.FAST,
        )
