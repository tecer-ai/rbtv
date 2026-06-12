"""Synchronous Manus API client for autonomous task execution."""
import json
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from .base import (
    Artifact,
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
        options = options or RequestOptions()

        # Build the task description from NON-system messages only. The runner
        # prepends a {files:...} chat-envelope system message that is irrelevant
        # to an autonomous Manus task and conflicts with a structured schema.
        description_parts: List[str] = []
        for message in messages:
            if message.role == "system":
                continue
            content = message.content
            if isinstance(content, list):
                content = json.dumps(content)
            description_parts.append(content)
        description = "\n".join(description_parts)

        create_body: Dict[str, Any] = {"message": {"content": description}}

        # Optional structured-output schema (read from extra_params, mirroring
        # gemini.py's extra_params["grounding"] handling).
        if options.extra_params is not None:
            schema = options.extra_params.get("structured_output_schema")
            if schema is not None:
                create_body["structured_output_schema"] = schema

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
                    json=create_body,
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

        attachments = self._collect_attachments(raw_messages)
        artifacts, artifact_errors = self._download_attachments(attachments, headers)
        structured_result = self._extract_structured_result(raw_messages)

        return Response(
            content=output_text,
            model=None,
            usage=None,
            raw_response={
                "task_id": task_id,
                "messages": raw_messages,
                "artifact_errors": artifact_errors,
            },
            artifacts=artifacts or None,
            structured_result=structured_result,
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

    def _collect_attachments(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Gather assistant_message attachments across all events.

        Inputs live on user_message; outputs on assistant_message. We want the
        agent's OUTPUT attachments only.
        """
        attachments: List[Dict[str, Any]] = []
        for event in messages:
            assistant_message = event.get("assistant_message")
            if not assistant_message:
                continue
            for att in assistant_message.get("attachments") or []:
                if att.get("url"):
                    attachments.append(att)
        return attachments

    def _download_attachments(
        self, attachments: List[Dict[str, Any]], headers: dict
    ) -> Tuple[List[Artifact], List[Dict[str, str]]]:
        """Download each attachment; a failure is non-fatal (recorded, skipped)."""
        artifacts: List[Artifact] = []
        errors: List[Dict[str, str]] = []

        for att in attachments:
            url = att.get("url")
            filename = att.get("filename") or "attachment"
            content_type = att.get("content_type")
            try:
                content = self._fetch_one(url, headers)
                artifacts.append(
                    Artifact(
                        filename=filename,
                        content=content,
                        content_type=content_type,
                        source_url=url,
                    )
                )
            except Exception as exc:  # noqa: BLE001 — a bad download must not crash the task
                errors.append({"filename": filename, "url": url or "", "error": str(exc)})

        return artifacts, errors

    def _fetch_one(self, url: str, headers: dict) -> bytes:
        """Fetch one attachment URL with a single GET; raise on any non-OK status.

        Manus serves every output artifact via a CloudFront *presigned* URL whose
        query signature carries the authorization — the x-manus-api-key header is
        ignored by the CDN (live-probed across 10 artifact types, 2026-06-11:
        `2-areas/rbtv/orchestration/manus-artifact-fetch/auth-probe/summary.md`).
        A single GET therefore suffices; the key header is kept as zero-cost
        insurance for a hypothetical api-gated artifact class. An invalid/expired
        signature returns a 403 (never a 200 login page), so a non-OK status is a
        real failure — raise it loud; the caller records it as a non-fatal
        per-file error rather than saving garbage bytes.
        """
        resp = requests.get(url, headers=headers, timeout=self.timeout)
        if resp.ok:
            return resp.content
        raise Exception(f"download failed: {resp.status_code}")

    def _extract_structured_result(self, messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Return the structured_output_result payload if a matching event exists."""
        for event in messages:
            if event.get("type") == "structured_output_result":
                result = event.get("structured_output_result")
                if result is not None:
                    return result
        return None
