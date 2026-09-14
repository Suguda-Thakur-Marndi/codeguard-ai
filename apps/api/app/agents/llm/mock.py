"""Scriptable Mock LLM Provider for offline deterministic testing and CI."""

import json
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar, cast

from pydantic import BaseModel

from app.agents.llm.provider import (
    LLMProvider,
    LLMResponse,
    ModelTier,
    TokenUsage,
)

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    """Deterministic scriptable mock provider supporting custom outputs, simulated errors, and token tracking."""

    def __init__(self) -> None:
        self.structured_handlers: list[tuple[Callable[[str, type], bool], Any]] = []
        self.text_handlers: list[tuple[Callable[[str], bool], str]] = []
        self.call_history: list[dict[str, Any]] = []
        self.simulated_error: Exception | None = None
        self.fail_n_times_then_succeed: int = 0
        self._current_failures: int = 0
        self.fixed_input_tokens: int = 420
        self.fixed_output_tokens: int = 180

    def register_structured_response(self, condition: Callable[[str, type], bool], response_data: Any) -> None:
        """Register a handler that returns response_data when condition(prompt, schema) evaluates to True."""
        self.structured_handlers.append((condition, response_data))

    def register_text_response(self, condition: Callable[[str], bool], response_text: str) -> None:
        """Register a handler that returns response_text when condition(prompt) evaluates to True."""
        self.text_handlers.append((condition, response_text))

    def set_error(self, error: Exception) -> None:
        """Force the provider to throw a specific error on subsequent calls."""
        self.simulated_error = error

    def set_transient_failure(self, error: Exception, failures: int = 1) -> None:
        """Fail `failures` times with `error`, then succeed normally."""
        self.simulated_error = error
        self.fail_n_times_then_succeed = failures
        self._current_failures = 0

    def clear(self) -> None:
        """Reset mock handlers, history, and error states."""
        self.structured_handlers.clear()
        self.text_handlers.clear()
        self.call_history.clear()
        self.simulated_error = None
        self.fail_n_times_then_succeed = 0
        self._current_failures = 0

    async def generate_structured(
        self,
        prompt: str,
        response_schema: type[T],
        system_instruction: str = "",
        model_tier: ModelTier = ModelTier.REASONING,
        temperature: float = 0.1,
        max_output_tokens: int | None = None,
    ) -> LLMResponse[T]:
        self.call_history.append(
            {
                "type": "structured",
                "prompt": prompt,
                "response_schema": response_schema,
                "system_instruction": system_instruction,
                "model_tier": model_tier,
            }
        )

        if self.simulated_error is not None:
            if self.fail_n_times_then_succeed > 0:
                if self._current_failures < self.fail_n_times_then_succeed:
                    self._current_failures += 1
                    raise self.simulated_error
                else:
                    self.simulated_error = None
            else:
                raise self.simulated_error

        # Check registered handlers
        for condition, response_obj in self.structured_handlers:
            if condition(prompt, response_schema):
                if callable(response_obj):
                    response_obj = response_obj(prompt, response_schema)

                if isinstance(response_obj, dict):
                    data = response_schema.model_validate(response_obj)
                    raw_str = json.dumps(response_obj)
                elif isinstance(response_obj, response_schema):
                    data = response_obj
                    raw_str = data.model_dump_json()
                elif isinstance(response_obj, str):
                    data = response_schema.model_validate_json(response_obj)
                    raw_str = response_obj
                else:
                    data = response_obj
                    raw_str = str(response_obj)

                tier_str = model_tier.value if hasattr(model_tier, "value") else str(model_tier)
                return LLMResponse(
                    data=cast(T, data),
                    model_name=f"mock-{tier_str}",
                    token_usage=TokenUsage(
                        input_tokens=self.fixed_input_tokens,
                        output_tokens=self.fixed_output_tokens,
                        total_tokens=self.fixed_input_tokens + self.fixed_output_tokens,
                        estimated_cost=0.0015,
                    ),
                    latency_ms=12.5,
                    raw_content=raw_str,
                )

        # Intelligent default instantiation for common review engine schemas
        from app.agents.schemas.comprehension import ComprehensionResult
        from app.agents.schemas.finding import SpecialistFindingsOutput

        if response_schema is ComprehensionResult:
            default_data = ComprehensionResult(
                intent="Implement requested code changes and improvements.",
                summary="Automated comprehension analysis for PR changes.",
                functional_changes=["Updated core logic in changed files."],
                refactors=[],
                changed_components=["core"],
                affected_interfaces=[],
                risk_areas=[],
                relevant_symbols=[],
            )
            raw_str = default_data.model_dump_json()
        elif response_schema is SpecialistFindingsOutput:
            default_data = SpecialistFindingsOutput(
                findings=[],
                analysis_summary="Analysis completed. No defects identified.",
            )
            raw_str = default_data.model_dump_json()
        else:
            try:
                default_data = response_schema()  # type: ignore[call-arg]
                raw_str = default_data.model_dump_json()
            except Exception:
                # Construct dummy dict with dummy values for required fields
                dummy_vals: dict[str, Any] = {}
                for field_name, field_info in getattr(response_schema, "model_fields", {}).items():
                    if field_info.is_required():
                        if field_info.annotation is str:
                            dummy_vals[field_name] = "mock_value"
                        elif field_info.annotation in (int, float):
                            dummy_vals[field_name] = 0
                        elif field_info.annotation is bool:
                            dummy_vals[field_name] = False
                        elif isinstance(field_info.annotation, type) and issubclass(field_info.annotation, Enum):
                            dummy_vals[field_name] = list(field_info.annotation)[0]
                        elif getattr(field_info.annotation, "__origin__", None) is list:
                            dummy_vals[field_name] = []
                        elif getattr(field_info.annotation, "__origin__", None) is dict:
                            dummy_vals[field_name] = {}
                        else:
                            dummy_vals[field_name] = None
                try:
                    default_data = response_schema.model_validate(dummy_vals)
                    raw_str = default_data.model_dump_json()
                except Exception:
                    default_data = response_schema.model_validate({})
                    raw_str = "{}"

        tier_str = model_tier.value if hasattr(model_tier, "value") else str(model_tier)
        return LLMResponse(
            data=cast(T, default_data),
            model_name=f"mock-{tier_str}",
            token_usage=TokenUsage(
                input_tokens=self.fixed_input_tokens,
                output_tokens=self.fixed_output_tokens,
                total_tokens=self.fixed_input_tokens + self.fixed_output_tokens,
                estimated_cost=0.0015,
            ),
            latency_ms=10.0,
            raw_content=raw_str,
        )

    async def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
        model_tier: ModelTier = ModelTier.FAST,
        temperature: float = 0.2,
        max_output_tokens: int | None = None,
    ) -> LLMResponse[str]:
        self.call_history.append(
            {
                "type": "text",
                "prompt": prompt,
                "system_instruction": system_instruction,
                "model_tier": model_tier,
            }
        )

        if self.simulated_error is not None:
            if self.fail_n_times_then_succeed > 0:
                if self._current_failures < self.fail_n_times_then_succeed:
                    self._current_failures += 1
                    raise self.simulated_error
                else:
                    self.simulated_error = None
            else:
                raise self.simulated_error

        tier_str = model_tier.value if hasattr(model_tier, "value") else str(model_tier)
        for condition, text in self.text_handlers:
            if condition(prompt):
                return LLMResponse(
                    data=text,
                    model_name=f"mock-{tier_str}",
                    token_usage=TokenUsage(
                        input_tokens=self.fixed_input_tokens,
                        output_tokens=self.fixed_output_tokens,
                        total_tokens=self.fixed_input_tokens + self.fixed_output_tokens,
                        estimated_cost=0.0005,
                    ),
                    latency_ms=8.0,
                    raw_content=text,
                )

        return LLMResponse(
            data="Mock text response",
            model_name=f"mock-{tier_str}",
            token_usage=TokenUsage(
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                estimated_cost=0.0003,
            ),
            latency_ms=5.0,
            raw_content="Mock text response",
        )
