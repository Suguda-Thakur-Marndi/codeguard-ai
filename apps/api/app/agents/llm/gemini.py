"""Gemini API LLM Provider implementation using google-genai SDK."""

import asyncio
import json
import random
import time
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.agents.llm.provider import (
    LLMAuthenticationError,
    LLMError,
    LLMProvider,
    LLMRateLimitError,
    LLMResponse,
    LLMTimeoutError,
    LLMValidationError,
    ModelTier,
    TokenUsage,
)
from app.core.config import settings
from app.core.logging import logger

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    """Production LLM provider integrating Google Gemini API via official google-genai SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        fast_model: str | None = None,
        reasoning_model: str | None = None,
        max_retries: int | None = None,
        timeout_seconds: float | None = None,
        retry_delay: float | None = None,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.fast_model = fast_model or settings.GEMINI_MODEL_FAST
        self.reasoning_model = reasoning_model or settings.GEMINI_MODEL_REASONING
        self.max_retries = max_retries if max_retries is not None else settings.AGENT_MAX_RETRIES
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.AGENT_TIMEOUT_SECONDS
        self.retry_delay = retry_delay

        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            if not self.api_key:
                raise LLMAuthenticationError(
                    "GEMINI_API_KEY is not configured. Configure GEMINI_API_KEY in .env or settings."
                )
            try:
                from google import genai

                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                raise LLMError(f"Failed to initialize Gemini client: {e}", original_error=e) from e
        return self._client

    def _resolve_model(self, tier: ModelTier) -> str:
        if tier == ModelTier.FAST:
            return self.fast_model
        return self.reasoning_model

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model_tier: ModelTier = ModelTier.REASONING,
    ) -> TokenUsage:
        """Calculate token usage and pricing for given tokens and model tier."""
        model = self._resolve_model(model_tier)
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        return TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost=cost,
        )

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        is_fast = model == self.fast_model
        in_rate = (
            settings.PRICE_PER_MILLION_INPUT_TOKENS_FAST
            if is_fast
            else settings.PRICE_PER_MILLION_INPUT_TOKENS_REASONING
        )
        out_rate = (
            settings.PRICE_PER_MILLION_OUTPUT_TOKENS_FAST
            if is_fast
            else settings.PRICE_PER_MILLION_OUTPUT_TOKENS_REASONING
        )
        cost = (input_tokens / 1_000_000.0) * in_rate + (output_tokens / 1_000_000.0) * out_rate
        return round(cost, 6)

    async def _execute_with_retry(
        self,
        func: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a call with exponential backoff and jitter for transient errors."""
        import inspect

        attempt = 0
        last_exception: Exception | None = None

        while attempt <= self.max_retries:
            try:
                # Support both async coroutine and sync callable
                if inspect.iscoroutinefunction(func):
                    return await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=self.timeout_seconds,
                    )
                else:
                    loop = asyncio.get_running_loop()
                    res = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: func(*args, **kwargs)),
                        timeout=self.timeout_seconds,
                    )
                    if inspect.isawaitable(res):
                        res = await res
                    return res
            except TimeoutError as e:
                attempt += 1
                last_exception = LLMTimeoutError(f"Gemini API timed out after {self.timeout_seconds}s", original_error=e)
                if attempt > self.max_retries:
                    break
                backoff = (self.retry_delay * (2**attempt)) if self.retry_delay is not None else ((2**attempt) + random.uniform(0.1, 0.5))
                logger.warning(f"Gemini timeout on attempt {attempt}. Retrying in {backoff:.2f}s...")
                await asyncio.sleep(backoff)
            except Exception as e:
                error_str = str(e).lower()
                # Categorize errors
                if "401" in error_str or "unauthenticated" in error_str or "api_key" in error_str:
                    raise LLMAuthenticationError(f"Gemini authentication failed: {e}", original_error=e) from e
                if "400" in error_str and "invalid_argument" in error_str:
                    raise LLMError(f"Gemini bad request: {e}", retryable=False, original_error=e) from e

                # Transient errors: 429, resource_exhausted, 503, unavailable
                is_transient = (
                    "429" in error_str
                    or "resource_exhausted" in error_str
                    or "rate limit" in error_str
                    or "503" in error_str
                    or "unavailable" in error_str
                    or "500" in error_str
                    or "internal" in error_str
                )
                if not is_transient:
                    raise LLMError(f"Gemini non-retryable error: {e}", retryable=False, original_error=e) from e

                attempt += 1
                last_exception = (
                    LLMRateLimitError(f"Gemini rate limit exceeded: {e}", original_error=e)
                    if ("429" in error_str or "rate limit" in error_str)
                    else LLMError(f"Gemini transient error: {e}", retryable=True, original_error=e)
                )
                if attempt > self.max_retries:
                    break
                backoff = (self.retry_delay * (2**attempt)) if self.retry_delay is not None else ((2**attempt) + random.uniform(0.1, 0.7))
                logger.warning(
                    f"Gemini transient error on attempt {attempt}: {e}. Retrying in {backoff:.2f}s..."
                )
                await asyncio.sleep(backoff)

        if isinstance(last_exception, LLMError):
            raise last_exception
        raise LLMError(f"Gemini request failed after {self.max_retries} retries: {last_exception}", original_error=last_exception)

    async def generate_structured(
        self,
        prompt: str,
        response_schema: type[T],
        system_instruction: str = "",
        model_tier: ModelTier = ModelTier.REASONING,
        temperature: float = 0.1,
        max_output_tokens: int | None = None,
    ) -> LLMResponse[T]:
        """Generate structured output validated against response_schema."""
        client = self._get_client()
        model_name = self._resolve_model(model_tier)
        t_start = time.perf_counter()

        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=response_schema,
            system_instruction=system_instruction if system_instruction else None,
            max_output_tokens=max_output_tokens,
        )

        response = await self._execute_with_retry(
            client.models.generate_content,
            model=model_name,
            contents=prompt,
            config=config,
        )

        latency_ms = (time.perf_counter() - t_start) * 1000.0

        # Extract tokens from usage metadata
        usage_meta = getattr(response, "usage_metadata", None)
        in_tokens = getattr(usage_meta, "prompt_token_count", 0) or 0
        out_tokens = getattr(usage_meta, "candidates_token_count", 0) or 0
        total_tokens = getattr(usage_meta, "total_token_count", in_tokens + out_tokens) or 0
        cost = self._calculate_cost(model_name, in_tokens, out_tokens)

        # Parse text into Pydantic schema
        raw_text = response.text or "{}"
        try:
            parsed_data = response_schema.model_validate_json(raw_text)
        except (ValidationError, json.JSONDecodeError) as err:
            logger.error(f"Failed to validate response against {response_schema.__name__}: {err}")
            raise LLMValidationError(
                f"Model response did not conform to schema {response_schema.__name__}: {err}",
                raw_response=raw_text,
                original_error=err,
            ) from err

        return LLMResponse(
            data=parsed_data,
            model_name=model_name,
            token_usage=TokenUsage(
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                total_tokens=total_tokens,
                estimated_cost=cost,
            ),
            latency_ms=round(latency_ms, 2),
            raw_content=raw_text,
        )

    async def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
        model_tier: ModelTier = ModelTier.FAST,
        temperature: float = 0.2,
        max_output_tokens: int | None = None,
    ) -> LLMResponse[str]:
        """Generate raw text response."""
        client = self._get_client()
        model_name = self._resolve_model(model_tier)
        t_start = time.perf_counter()

        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction if system_instruction else None,
            max_output_tokens=max_output_tokens,
        )

        response = await self._execute_with_retry(
            client.models.generate_content,
            model=model_name,
            contents=prompt,
            config=config,
        )

        latency_ms = (time.perf_counter() - t_start) * 1000.0

        usage_meta = getattr(response, "usage_metadata", None)
        in_tokens = getattr(usage_meta, "prompt_token_count", 0) or 0
        out_tokens = getattr(usage_meta, "candidates_token_count", 0) or 0
        total_tokens = getattr(usage_meta, "total_token_count", in_tokens + out_tokens) or 0
        cost = self._calculate_cost(model_name, in_tokens, out_tokens)

        return LLMResponse(
            data=response.text or "",
            model_name=model_name,
            token_usage=TokenUsage(
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                total_tokens=total_tokens,
                estimated_cost=cost,
            ),
            latency_ms=round(latency_ms, 2),
            raw_content=response.text or "",
        )
