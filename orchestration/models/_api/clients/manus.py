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
    structured_output = False

    def __init__(self) -> None:
        self.api_key: Optional[str] = None
        self.base_url = "https://api.manus.ai/v2"
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

        headers = {
            "Content-Type": "application/json",
            "x-manus-api-key": self.api_key,
        }

        last_error: Optional[Exception] = None
        task_id: Optional[str] = None

        for attempt in range(self.retries):
            try:
                resp = requests.post(
                    f"{self.base_url}/task.create",
                    headers=headers,
                    json={"message": {"content": description}},
                    timeout=30,
                )
            except requests.exceptions.RequestException as e:
                last_error = e
                time.sleep(2 ** attempt)
                continue

            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                last_error = Exception(f"Manus API error: {resp.status_code} - {resp.text}")
                time.sleep(2 ** attempt)
                continue

            if resp.status_code != 200:
                raise Exception(f"Manus API error: {resp.status_code} - {resp.text}")

            data = resp.json()
            task_id = data["task_id"]
            break

        if task_id is None:
            raise last_error if last_error is not None else Exception("Manus API error: max retries exceeded")

        output_text, raw_messages = self._poll_and_fetch_output(task_id, headers)
        return Response(
            content=output_text,
            model=None,
            usage=None,
            raw_response={"task_id": task_id, "messages": raw_messages},
        )

    def _poll_and_fetch_output(self, task_id: str, headers: dict) -> tuple:
        start = time.time()

        while time.time() - start < self.timeout:
            try:
                resp = requests.get(
                    f"{self.base_url}/task.detail",
                    headers=headers,
                    params={"task_id": task_id},
                    timeout=10,
                )
            except requests.exceptions.RequestException:
                time.sleep(2)
                continue

            if not resp.ok:
                raise Exception(f"Manus API error: {resp.status_code} - {resp.text}")

            data = resp.json()
            status = data["task"]["status"]

            if status == "stopped":
                break

            if status == "error":
                raise Exception("Task failed: " + str(data.get("task", {}).get("error", "unknown error")))

            if status in ("running", "waiting"):
                time.sleep(2)
                continue

            time.sleep(2)
        else:
            raise Exception("Task timeout")

        resp = requests.get(
            f"{self.base_url}/task.listMessages",
            headers=headers,
            params={"task_id": task_id, "order": "asc"},
            timeout=10,
        )

        if not resp.ok:
            raise Exception(f"Manus API error: {resp.status_code} - {resp.text}")

        data = resp.json()
        messages = data.get("messages", [])

        contents: List[str] = []
        for event in messages:
            assistant_message = event.get("assistant_message")
            if assistant_message is not None:
                content = assistant_message.get("content", "")
                if content:
                    contents.append(content)

        if contents:
            return "\n".join(contents), messages

        return json.dumps(data), messages
