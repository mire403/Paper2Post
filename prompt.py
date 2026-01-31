from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMClient:
    """
    Minimal OpenAI-compatible Chat Completions client.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout_s: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def chat(self, messages: List[ChatMessage], *, temperature: float = 0.4) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout_s) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )


def build_paper_context(*, title: str, sections: Dict[str, str], raw_text: str, max_chars: int = 18000) -> str:
    """
    Build a bounded-length context string for prompting.
    """
    preferred = ["abstract", "introduction", "method", "results", "discussion", "limitations", "conclusion"]
    parts: List[str] = []
    if title:
        parts.append(f"Title: {title}")
    for k in preferred:
        if k in sections and sections[k].strip():
            parts.append(f"\n## {k.title()}\n{sections[k].strip()}")

    # Fallback: if parsing failed, include head of raw text.
    if len(parts) <= 1:
        parts.append("\n## Paper Text (truncated)\n" + raw_text.strip())

    ctx = "\n".join(parts).strip()
    if len(ctx) > max_chars:
        ctx = ctx[:max_chars].rstrip() + "\n\n[TRUNCATED]"
    return ctx


def system_guardrails() -> str:
    return (
        "You are a scientific communication expert and an NLP engineer. "
        "Your job is to rewrite the given paper into platform-specific content while preserving technical accuracy. "
        "Do not invent results, numbers, datasets, metrics, or claims not supported by the provided text. "
        "If key details are missing, explicitly mark them as 'Not specified in the provided text'. "
        "Keep terminology precise; prefer concrete mechanisms over vague hype."
    )


def user_instruction(platform_brief: str, paper_context: str) -> str:
    return (
        f"{platform_brief}\n\n"
        "Paper context:\n"
        "----------------\n"
        f"{paper_context}\n"
        "----------------\n"
    )

