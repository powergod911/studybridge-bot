from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Literal, TypedDict
from zoneinfo import ZoneInfo

ResponseChannel = Literal["telegram", "web"]


class ChatTurn(TypedDict):
    role: Literal["user", "assistant"]
    content: str


def system_prompt(channel: ResponseChannel) -> str:
    now = datetime.now(ZoneInfo("Asia/Colombo")).strftime(
        "%A, %B %d, %Y, %I:%M %p Sri Lanka time"
    )
    base = (
        "You are Shadow Mentor, a reliable and encouraging Sri Lankan G.C.E. A/L study assistant. "
        "Never claim to be Claude, Anthropic, ChatGPT, or another assistant. "
        "Match the student's language, including Sinhala or English. "
        "Explain reasoning clearly, check calculations, and keep answers focused on the question. "
        "Treat the supplied conversation history as active context. Resolve follow-up phrases such "
        "as 'why', 'that step', 'another method', and their Sinhala equivalents from that history. "
        "Do not restart with a greeting or repeat the whole previous answer unless asked. "
        f"Current date/time context: {now}. Use it silently for time-sensitive answers. "
        "Do not mention the date or time unless the student asks or it is directly relevant. "
    )

    if channel == "telegram":
        return base + (
            "Format for a plain Telegram message. Do not use Markdown headings, bold markers, "
            "tables, code fences, or LaTeX delimiters. Never output #, **, $, $$, \\(, \\), \\[, "
            "or \\]. Use short numbered steps and readable Unicode maths such as ρ, ΔU, h², ×, "
            "and (1/2)Aρgh². Keep the final answer easy to scan."
        )

    return base + (
        "Format for a modern study web app using clean Markdown. Use short headings and lists only "
        "when helpful. Write inline maths inside \\(...\\) and display equations inside \\[...\\]. "
        "Use valid LaTeX and keep derivations readable. Do not wrap the entire answer in a code block."
    )


def normalize_history(history: Sequence[ChatTurn] | None, limit: int = 8) -> list[ChatTurn]:
    if not history:
        return []

    normalized: list[ChatTurn] = []
    for turn in history[-limit:]:
        role = turn.get("role")
        content = turn.get("content", "").strip()
        if role in {"user", "assistant"} and content:
            normalized.append({"role": role, "content": content[:6000]})
    return normalized


def prompt_with_history(prompt: str, history: Sequence[ChatTurn] | None) -> str:
    normalized = normalize_history(history)
    if not normalized:
        return prompt

    lines = ["Previous conversation context:"]
    for turn in normalized:
        speaker = "Student" if turn["role"] == "user" else "Shadow Mentor"
        lines.append(f"{speaker}: {turn['content']}")
    lines.extend(("", f"Current student question: {prompt}"))
    return "\n\n".join(lines)
