from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any


DEFAULT_LOCAL_MODEL = "hf.co/unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M"


DEFAULT_SYSTEM_PROMPT = """You convert Korean public-office drafting requests into strict JSON.
Return only JSON matching this shape:
{
  "title": "...",
  "sender": "...",
  "recipients": ["..."],
  "date": "YYYY-MM-DD",
  "registration_number": "...",
  "classification": "공개",
  "body": [{"type": "paragraph", "text": "..."}, {"type": "table", "headers": [], "rows": []}],
  "attachments": [{"title": "...", "count": "1부"}],
  "approval": [{"role": "담당", "name": ""}],
  "contact": "..."
}
Use concise official Korean. Do not invent legal facts when missing.
"""


class OpenCompatibleLLM:
    """Small OpenAI-compatible client for Ollama, vLLM, LM Studio, and similar local LLM servers."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: int = 120,
    ) -> None:
        self.base_url = (base_url or os.getenv("OPENAI_COMPATIBLE_BASE_URL") or "http://localhost:11434/v1").rstrip("/")
        self.model = model or os.getenv("OPENAI_COMPATIBLE_MODEL") or DEFAULT_LOCAL_MODEL
        self.api_key = api_key or os.getenv("OPENAI_COMPATIBLE_API_KEY") or "local"
        self.timeout = timeout

    def draft_document_json(self, prompt: str, *, system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc

        content = data["choices"][0]["message"]["content"]
        return parse_json_content(content)


def parse_json_content(content: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.S)
        if not match:
            raise
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("LLM response must be a JSON object")
    return value
