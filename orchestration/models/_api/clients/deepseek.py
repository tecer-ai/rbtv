"""Synchronous DeepSeek API client (OpenAI-compatible)."""
import json
import time
from typing import List, Optional

import requests

from .base import (
    Message,
    ProviderClient,
    ProviderConfig,
    ProviderName,
    RequestOptions,
    Response,
    TokenUsage,
)


class DeepSeekClient(ProviderClient):
    structured_output: bool = True

    def __init__(self) -> None:
        self.api_key: Optional[str] = None
        self.base_url = "https://api.deepseek.com/v1"
        self.timeout = 60
        self.retries = 3

    @property
    def name(self) -> ProviderName:
        return ProviderName.DEEPSEEK

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
            raise ValueError("DeepSeek: options.model is required (pass --model)")

        payload: dict = {
            "model": options.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }

        if options.temperature is not None:
            payload["temperature"] = options.temperature
        if options.top_p is not None:
            payload["top_p"] = options.top_p
        if options.max_tokens is not None:
            payload["max_tokens"] = options.max_tokens
        if options.stop_sequences is not None:
            payload["stop"] = options.stop_sequences

        if self.structured_output:
            payload["response_format"] = {"type": "json_object"}

        if options.extra_params is not None:
            payload.update(options.extra_params)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        url = f"{self.base_url}/chat/completions"
        last_error: Exception

        for attempt in range(self.retries):
            try:
                resp = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )

                if resp.status_code == 429 or 500 <= resp.status_code < 600:
                    last_error = Exception(f"DeepSeek API error: {resp.status_code} - {resp.text}")
                    time.sleep(2 ** attempt)
                    continue

                if 400 <= resp.status_code < 500:
                    raise Exception(f"DeepSeek API error: {resp.status_code} - {resp.text}")

                if not resp.ok:
                    raise Exception(f"DeepSeek API error: {resp.status_code} - {resp.text}")

                data = resp.json()
                usage_data = data.get("usage")
                usage = (
                    TokenUsage(
                        input_tokens=usage_data.get("prompt_tokens", 0),
                        output_tokens=usage_data.get("completion_tokens", 0),
                        total_tokens=usage_data.get("total_tokens", 0),
                    )
                    if usage_data
                    else None
                )

                return Response(
                    content=data["choices"][0]["message"].get("content", ""),
                    model=data.get("model"),
                    usage=usage,
                    raw_response=data,
                )

            except requests.exceptions.RequestException as e:
                last_error = e
                time.sleep(2 ** attempt)
                continue

        raise last_error
