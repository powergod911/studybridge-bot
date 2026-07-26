from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path
from uuid import UUID

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

    def test_chat_request_accepts_conversation_id(self) -> None:
        request = ChatRequest.model_validate(
            {
                "message": "Why does that step work?",
                "conversation_id": "1b671a64-40d5-491e-99b0-da01ff1f3341",
            }
        )
        self.assertEqual(
            request.conversation_id,
            UUID("1b671a64-40d5-491e-99b0-da01ff1f3341"),
        )

    def test_index_contains_no_inline_scripts(self) -> None:
        parser = ScriptParser()
        parser.feed((ROOT / "web/static/index.html").read_text(encoding="utf-8"))
        self.assertEqual(parser.inline_scripts, 0)

    def test_theme_bootstrap_is_external(self) -> None:
        html = (ROOT / "web/static/index.html").read_text(encoding="utf-8")
        self.assertIn('src="/static/theme-init.js"', html)

    def test_index_exposes_history_model_menu_and_ict(self) -> None:
        html = (ROOT / "web/static/index.html").read_text(encoding="utf-8")
        script = (ROOT / "web/static/app.js").read_text(encoding="utf-8")
        self.assertIn('id="conversationList"', html)
        self.assertIn('id="modelMenu"', html)
        self.assertIn('["ICT", "Help me with this A/L ICT question: "]', script)

    def test_frontend_sends_conversation_and_accepts_pasted_images(self) -> None:
        script = (ROOT / "web/static/app.js").read_text(encoding="utf-8")
        self.assertIn("conversation_id: state.activeConversationId", script)
        self.assertIn('elements.input.addEventListener("paste"', script)
        self.assertIn("imageItem?.getAsFile()", script)


if __name__ == "__main__":
    unittest.main()
