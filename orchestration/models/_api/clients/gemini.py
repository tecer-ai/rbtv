"""Synchronous Google Gemini client for the API runner."""
import json
import time
from typing import Any, Dict, List, Optional

import requests

from .base import Message, ProviderClient, ProviderConfig, ProviderName, RequestOptions, Response, TokenUsage


# Default visible-answer budget for the JSON-envelope (non-grounded) path —
# matches the gemini-api manifest's documented max_output.
_DEFAULT_MAX_OUTPUT_TOKENS = 8192

# Grounded budget. On the 3.x flash class extended thinking is ON by default and
# its tokens are billed against maxOutputTokens, so the cap MUST cover
# thinking + the full answer or the visible answer is starved — truncated, or
# replaced by leaked reasoning. Live repro 2026-06-24: a grounded research brief
# spent 4727 thinking tokens, overrunning the old 4096 cap, and landed a
# 612-byte truncated dump; at 16384 the same call returned the full ~7.5KB
# answer (thinking ~5k + answer ~2k, well within budget). 16384 gives ~3x margin
# over observed thinking for a light single-call grounded lookup.
_GROUNDED_MAX_OUTPUT_TOKENS = 16384


class GeminiClient(ProviderClient):
    structured_output: bool = True

    def __init__(self) -> None:
        self.api_key: Optional[str] = None
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.timeout = 60
        self.retries = 3

    @property
    def name(self) -> ProviderName:
        return ProviderName.GEMINI

    def initialize(self, config: ProviderConfig) -> None:
        self.api_key = config.api_key
        if config.base_url is not None:
            self.base_url = config.base_url
        if config.timeout is not None:
            self.timeout = config.timeout
        if config.retries is not None:
            self.retries = config.retries

    def chat(self, messages: List[Message], options: Optional[RequestOptions] = None) -> Response:
        options = options or RequestOptions()
        if not options.model:
            raise ValueError("Gemini: options.model is required (pass --model)")
        payload = self._build_payload(messages, options)
        return self._execute_with_retry(payload, options.model)

    def _build_payload(self, messages: List[Message], options: RequestOptions) -> Dict[str, Any]:
        system_texts: List[str] = []
        contents: List[Dict[str, Any]] = []

        for message in messages:
            if message.role == "system":
                system_texts.append(message.content)
            else:
                role = "model" if message.role == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": message.content}]})

        payload: Dict[str, Any] = {"contents": contents}

        if system_texts:
            payload["systemInstruction"] = {"parts": [{"text": "\n".join(system_texts)}]}

        grounding = False
        if options.extra_params is not None:
            grounding = bool(options.extra_params.get("grounding"))

        # Grounded calls run extended thinking that is billed against maxOutputTokens,
        # so they get a larger default budget to avoid starving the visible answer.
        default_max_output = _GROUNDED_MAX_OUTPUT_TOKENS if grounding else _DEFAULT_MAX_OUTPUT_TOKENS
        generation_config: Dict[str, Any] = {"maxOutputTokens": options.max_tokens or default_max_output}

        if options.temperature is not None:
            generation_config["temperature"] = options.temperature
        if options.top_p is not None:
            generation_config["topP"] = options.top_p
        if options.stop_sequences is not None:
            generation_config["stopSequences"] = options.stop_sequences

        if grounding:
            payload["tools"] = [{"google_search": {}}]
        else:
            generation_config["responseMimeType"] = "application/json"

        payload["generationConfig"] = generation_config

        if options.extra_params is not None:
            for key, value in options.extra_params.items():
                if key != "grounding":
                    payload[key] = value

        return payload

    def _execute_with_retry(self, payload: Dict[str, Any], model: str) -> Response:
        url = f"{self.base_url}/models/{model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        last_exception: Optional[Exception] = None

        for attempt in range(self.retries):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            except requests.exceptions.RequestException as exc:
                last_exception = exc
                time.sleep(2 ** attempt)
                continue

            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                last_exception = Exception(f"Gemini API error: {resp.status_code} - {resp.text}")
                time.sleep(2 ** attempt)
                continue

            if resp.status_code != 200:
                raise Exception(f"Gemini API error: {resp.status_code} - {resp.text}")

            data = resp.json()
            return self._parse_response(data, model)

        raise last_exception if last_exception is not None else Exception("Gemini API error: max retries exceeded")

    def _parse_response(self, data: Dict[str, Any], model: str) -> Response:
        candidates = data.get("candidates") or [{}]
        candidate = candidates[0]

        content_parts = candidate.get("content", {}).get("parts", [])
        content = "".join(part.get("text", "") for part in content_parts)

        usage = None
        usage_metadata = data.get("usageMetadata")
        if usage_metadata is not None:
            usage = TokenUsage(
                input_tokens=usage_metadata.get("promptTokenCount", 0),
                output_tokens=usage_metadata.get("candidatesTokenCount", 0),
                total_tokens=usage_metadata.get("totalTokenCount", 0),
            )

        gem_fr = candidate.get("finishReason")
        if gem_fr == "STOP":
            mapped_finish_reason = "stop"
        elif gem_fr == "MAX_TOKENS":
            mapped_finish_reason = "length"
        elif gem_fr is not None:
            mapped_finish_reason = gem_fr.lower()
        else:
            mapped_finish_reason = None

        raw_response = dict(data)
        raw_response["choices"] = [{"finish_reason": mapped_finish_reason}]

        return Response(
            content=content,
            model=data.get("modelVersion") or model,
            usage=usage,
            raw_response=raw_response,
        )
