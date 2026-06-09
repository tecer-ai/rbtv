"""Synchronous Manus API client for autonomous task execution."""
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
)


class ManusClient(ProviderClient):
    structured_output: bool = False

    def __init__(self) -> None:
        self.api_key: Optional[str] = None
        self.base_url = "https://api.manus.im/v1"
        self.timeout = 300
        self.retries = 3

    @property
    def name(self) -> ProviderName:
        return ProviderName.MANUS

    def initialize(self, config: ProviderConfig) -> None:
        self.api_key = config.api_key
        if config.base_url is not None:
            self.base_url = config.base_url
        if config.timeout is not None:
            self.timeout = config.timeout
        if config.retries is not None:
            self.retries = config.retries

    def chat(self, messages: List[Message], options: Optional[RequestOptions] = None) -> Response:
        description_parts: List[str] = []
        for message in messages:
            content = message.content
            if isinstance(content, list):
                content = json.dumps(content)
            description_parts.append(content)
        description = "\n".join(description_parts)

        payload = {
            "description": description,
            "autonomy_level": "high",
            "timeout": self.timeout,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        last_error: Optional[Exception] = None

        for attempt in range(self.retries):
            try:
                resp = requests.post(
                    f"{self.base_url}/tasks",
                    headers=headers,
                    json=payload,
                    timeout=30,
                )
            except requests.exceptions.RequestException as e:
                last_error = e
                time.sleep(2 ** attempt)
                continue

            if resp.status_code == 201:
                data = resp.json()
                task_id = data["task_id"]
                output = self._poll_task_result(task_id, headers)
                if isinstance(output, str):
                    content = output
                else:
                    try:
                        content = json.dumps(output)
                    except (TypeError, ValueError):
                        content = str(output)
                return Response(
                    content=content,
                    model=None,
                    usage=None,
                    raw_response={"task_id": task_id, "output": output},
                )

            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                last_error = Exception(f"Manus API error: {resp.status_code} - {resp.text}")
                time.sleep(2 ** attempt)
                continue

            raise Exception(f"Manus API error: {resp.status_code} - {resp.text}")

        if last_error is not None:
            raise last_error
        raise Exception("Manus API error: max retries exceeded")

    def _poll_task_result(self, task_id: str, headers: dict) -> object:
        start = time.time()
        url = f"{self.base_url}/tasks/{task_id}"

        while time.time() - start < self.timeout:
            try:
                resp = requests.get(url, headers=headers, timeout=10)
            except requests.exceptions.RequestException as e:
                time.sleep(2)
                continue

            if not resp.ok:
                raise Exception(f"Manus API error: {resp.status_code} - {resp.text}")

            data = resp.json()
            status = data.get("status")

            if status == "completed":
                return data.get("output", {})

            if status == "failed":
                raise Exception(f"Task failed: {data.get('error', 'unknown error')}")

            time.sleep(2)

        raise Exception("Task timeout")
