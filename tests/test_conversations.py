from __future__ import annotations

import unittest

from bot.router import Engine
from web.conversations import build_conversation_title
from web.main import _select_engine
from web.schemas import ChatRequest


class ConversationTests(unittest.TestCase):
    def test_follow_up_keeps_previous_engine_in_auto_mode(self) -> None:
        engine = _select_engine(
            ChatRequest(message="Why does that step work?"),
            has_history=True,
            last_engine=Engine.DEEPSEEK,
        )
        self.assertEqual(engine, Engine.DEEPSEEK)

    def test_explicit_engine_overrides_follow_up_routing(self) -> None:
        engine = _select_engine(
            ChatRequest(message="Why?", engine="gemini"),
            has_history=True,
            last_engine=Engine.DEEPSEEK,
        )
        self.assertEqual(engine, Engine.GEMINI)

    def test_conversation_title_is_short_and_single_line(self) -> None:
        title = build_conversation_title(
            "  Explain\nwhy the centre of mass moves after these liquids mix "
            "and compare both states.  "
        )
        self.assertLessEqual(len(title), 54)
        self.assertNotIn("\n", title)
        self.assertTrue(title.endswith("..."))

    def test_default_image_prompt_gets_useful_title(self) -> None:
        self.assertEqual(
            build_conversation_title(
                "Explain this image step-by-step.",
                has_image=True,
            ),
            "Study image",
        )


if __name__ == "__main__":
    unittest.main()
