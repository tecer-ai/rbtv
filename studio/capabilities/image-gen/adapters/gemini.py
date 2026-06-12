"""Gemini image generation adapter.

Uses the Generative Language REST API. Model: gemini-3.1-flash-image.
"""

import base64
from pathlib import Path

import requests

API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent"


def generate(prompt: str, out_path: str, fmt: str, aspect: str | None = None, api_key: str | None = None) -> None:
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required but not provided.")

    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }

    body: dict = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                ],
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }

    if aspect:
        body["generationConfig"]["imageConfig"] = {
            "aspectRatio": aspect,
        }

    resp = requests.post(API_ENDPOINT, headers=headers, json=body, timeout=120)

    if resp.status_code != 200:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise RuntimeError(f"Gemini API error HTTP {resp.status_code}: {detail}")

    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini API returned no candidates.")

    image_found = False
    for part in candidates[0].get("content", {}).get("parts", []):
        inline_data = part.get("inlineData")
        if inline_data:
            b64_data = inline_data.get("data", "")
            if b64_data:
                image_bytes = base64.b64decode(b64_data)
                Path(out_path).write_bytes(image_bytes)
                image_found = True
                break

    if not image_found:
        raise RuntimeError("Gemini API returned no image data in response.")
