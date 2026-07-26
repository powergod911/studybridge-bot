from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path

from pydantic import ValidationError

from web.schemas import ChatRequest

ROOT = Path(__file__).parents[1]


class ScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.inline_scripts = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag == "script" and not dict(attrs).get("src"):
            self.inline_scripts += 1


class WebContractTests(unittest.TestCase):
    def test_history_accepts_transport_limit(self) -> None:
        request = ChatRequest.model_validate(
            {
                "message": "next",
                "history": [{"role": "assistant", "content": "x" * 6000}],
            }
        )
        self.assertEqual(len(request.history[0].content), 6000)

    def test_history_rejects_content_above_transport_limit(self) -> None:
        with self.assertRaises(ValidationError):
            ChatRequest.model_validate(
                {
                    "message": "next",
                    "history": [{"role": "assistant", "content": "x" * 6001}],
                }
            )

    def test_index_contains_no_inline_scripts(self) -> None:
        parser = ScriptParser()
        parser.feed((ROOT / "web/static/index.html").read_text(encoding="utf-8"))
        self.assertEqual(parser.inline_scripts, 0)

    def test_theme_bootstrap_is_external(self) -> None:
        html = (ROOT / "web/static/index.html").read_text(encoding="utf-8")
        self.assertIn('src="/static/theme-init.js"', html)


if __name__ == "__main__":
    unittest.main()
