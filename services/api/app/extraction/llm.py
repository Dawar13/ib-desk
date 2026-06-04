"""OpenAI client with structured outputs and cassette record/replay.

Modes (from settings.llm_mode):
  - replay: load a recorded response from the cassette directory by its logical
    id. No network and no secret, so the pipeline logic gates run anywhere.
  - live: call OpenAI with the configured per-pass model and a response format
    constrained to the pydantic schema, returning the parsed object and token
    usage.
  - record: call live and write the response to a cassette for later replay.

Temperature is not sent: gpt-5 class models constrain it, and per the spec the
deterministic normalization and verification passes, not the model temperature,
carry value consistency.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar, cast

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int
    # Input tokens served from the prompt cache (the document re-sent across a
    # run's section calls). Billed at the cheaper cached rate; tracked so the
    # caching savings are visible. Zero when nothing was cached.
    cached_prompt_tokens: int = 0


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, mode: str, api_key: str | None, cassette_dir: str) -> None:
        self._mode = mode
        self._api_key = api_key
        self._cassette_dir = Path(cassette_dir)

    def _cassette_path(self, logical_id: str) -> Path:
        return self._cassette_dir / (_UNSAFE.sub("_", logical_id) + ".json")

    def complete(
        self,
        logical_id: str,
        model: str,
        messages: list[dict[str, str]],
        schema: type[T],
    ) -> tuple[T, Usage]:
        if self._mode == "replay":
            return self._replay(logical_id, schema)
        parsed, usage = self._live(model, messages, schema)
        if self._mode == "record":
            self._save(logical_id, parsed, usage)
        return parsed, usage

    def _replay(self, logical_id: str, schema: type[T]) -> tuple[T, Usage]:
        path = self._cassette_path(logical_id)
        if not path.exists():
            raise LLMError(f"No cassette for '{logical_id}' at {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        parsed = schema.model_validate(payload["data"])
        usage_payload = payload.get("usage", {})
        usage = Usage(
            prompt_tokens=int(usage_payload.get("prompt_tokens", 0)),
            completion_tokens=int(usage_payload.get("completion_tokens", 0)),
            cached_prompt_tokens=int(usage_payload.get("cached_prompt_tokens", 0)),
        )
        return parsed, usage

    def _live(self, model: str, messages: list[dict[str, str]], schema: type[T]) -> tuple[T, Usage]:
        if not self._api_key:
            raise LLMError("Live LLM mode requires OPENAI_API_KEY to be set")
        if not model:
            raise LLMError("Live LLM mode requires the per-pass model to be set")
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)
        parser: Any = getattr(client.chat.completions, "parse", None)
        if parser is None:  # older SDKs expose it under beta
            parser = client.beta.chat.completions.parse
        completion = parser(model=model, messages=messages, response_format=schema)
        message = completion.choices[0].message
        parsed_obj = getattr(message, "parsed", None)
        if parsed_obj is None:
            refusal = getattr(message, "refusal", None)
            raise LLMError(f"Model returned no parsed output (refusal: {refusal})")
        usage_obj = completion.usage
        # OpenAI reports cached input tokens under prompt_tokens_details.cached_tokens.
        details = getattr(usage_obj, "prompt_tokens_details", None)
        cached = int(getattr(details, "cached_tokens", 0) or 0) if details is not None else 0
        usage = Usage(
            prompt_tokens=int(getattr(usage_obj, "prompt_tokens", 0) or 0),
            completion_tokens=int(getattr(usage_obj, "completion_tokens", 0) or 0),
            cached_prompt_tokens=cached,
        )
        return cast(T, parsed_obj), usage

    def _save(self, logical_id: str, parsed: BaseModel, usage: Usage) -> None:
        self._cassette_dir.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "data": parsed.model_dump(),
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "cached_prompt_tokens": usage.cached_prompt_tokens,
            },
        }
        self._cassette_path(logical_id).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def get_llm() -> LLMClient:
    """Build the LLM client from settings (mode, key, cassette directory)."""
    from app.config import get_settings

    settings = get_settings()
    return LLMClient(
        mode=settings.llm_mode,
        api_key=settings.openai_api_key,
        cassette_dir=settings.cassette_dir,
    )
