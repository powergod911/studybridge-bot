from __future__ import annotations

import re

LATEX_REPLACEMENTS = {
    r"\rho": "ρ",
    r"\Delta": "Δ",
    r"\delta": "δ",
    r"\theta": "θ",
    r"\alpha": "α",
    r"\beta": "β",
    r"\gamma": "γ",
    r"\lambda": "λ",
    r"\mu": "μ",
    r"\pi": "π",
    r"\cdot": "·",
    r"\times": "×",
    r"\pm": "±",
    r"\leq": "≤",
    r"\geq": "≥",
    r"\neq": "≠",
    r"\rightarrow": "→",
}


def format_telegram_text(text: str) -> str:
    formatted = text.strip()
    formatted = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", formatted)
    formatted = re.sub(r"\$\$(.*?)\$\$", r"\1", formatted, flags=re.DOTALL)
    formatted = re.sub(r"\$(.*?)\$", r"\1", formatted, flags=re.DOTALL)
    formatted = re.sub(r"\\\((.*?)\\\)", r"\1", formatted, flags=re.DOTALL)
    formatted = re.sub(r"\\\[(.*?)\\\]", r"\1", formatted, flags=re.DOTALL)
    formatted = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1/\2)", formatted)

    for latex, unicode_value in LATEX_REPLACEMENTS.items():
        formatted = formatted.replace(latex, unicode_value)

    formatted = formatted.replace(r"\left", "").replace(r"\right", "")
    formatted = formatted.replace("**", "").replace("__", "").replace("`", "")
    formatted = re.sub(r"(?m)^\s*[-*]\s+", "• ", formatted)
    formatted = re.sub(r"\n{3,}", "\n\n", formatted)
    return formatted.strip()


def split_telegram_text(text: str, limit: int = 3900) -> list[str]:
    remaining = text.strip()
    chunks: list[str] = []

    while len(remaining) > limit:
        split_at = remaining.rfind("\n\n", 0, limit)
        if split_at < limit // 2:
            split_at = remaining.rfind("\n", 0, limit)
        if split_at < limit // 2:
            split_at = remaining.rfind(" ", 0, limit)
        if split_at <= 0:
            split_at = limit
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    if remaining:
        chunks.append(remaining)
    return chunks or ["I could not generate an answer."]
