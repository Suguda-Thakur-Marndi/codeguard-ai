"""LLM Provider abstraction and common response models."""

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")
T_Schema = TypeVar("T_Schema", bound=BaseModel)


class ModelTier(enum.StrEnum):
    FAST = "fast"
    REASONING = "reasoning"


class LLMError(Exception):
    """Base exception for LLM provider errors."""

    def __init__(self, message: str, retryable: bool = False, original_error: Exception | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.original_error = original_error


class LLMRateLimitError(LLMError):
    """Raised when the LLM provider returns a 429 rate limit error."""

    def __init__(self, message: str = "Rate limit exceeded", original_error: Exception | None = None):
        super().__init__(message=message, retryable=True, original_error=original_error)


class LLMTimeoutError(LLMError):
    """Raised when an LLM provider call times out."""

    def __init__(self, message: str = "LLM request timed out", original_error: Exception | None = None):
        super().__init__(message=message, retryable=True, original_error=original_error)


class LLMAuthenticationError(LLMError):
    """Raised when credentials or API key are invalid (non-retryable)."""

    def __init__(self, message: str = "Authentication failed", original_error: Exception | None = None):
        super().__init__(message=message, retryable=False, original_error=original_error)


class LLMValidationError(LLMError):
    """Raised when model response cannot be parsed into the expected Pydantic schema."""

    def __init__(self, message: str, raw_response: str = "", original_error: Exception | None = None):
        super().__init__(message=message, retryable=True, original_error=original_error)
        self.raw_response = raw_response


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0


@dataclass
class LLMResponse(Generic[T]):
    """Standardized response container returned by all LLM providers."""

    data: T
    model_name: str
    token_usage: TokenUsage
    latency_ms: float
    retries_attempted: int = 0
    raw_content: str = ""
    extra_metadata: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Abstract interface for all Large Language Model integrations."""

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_schema: type[T_Schema],
        system_instruction: str = "",
        model_tier: ModelTier = ModelTier.REASONING,
        temperature: float = 0.1,
        max_output_tokens: int | None = None,
    ) -> LLMResponse[T_Schema]:
        """Generate a structured response guaranteed to conform to response_schema."""
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
        model_tier: ModelTier = ModelTier.FAST,
        temperature: float = 0.2,
        max_output_tokens: int | None = None,
    ) -> LLMResponse[str]:
        """Generate raw text response."""
        pass
