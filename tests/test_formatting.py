from __future__ import annotations

import unittest

from bot.formatting import format_telegram_text, split_telegram_text


class TelegramFormattingTests(unittest.TestCase):
    def test_removes_markdown_and_latex_delimiters(self) -> None:
        source = "### **Answer**\n\n$$\\Delta U = \\frac{1}{2}A\\rho gh^2$$"
        result = format_telegram_text(source)
        self.assertEqual(result, "Answer\n\nΔ U = (1/2)Aρ gh^2")
        self.assertNotIn("$", result)
        self.assertNotIn("**", result)

    def test_splits_on_readable_boundaries(self) -> None:
        result = split_telegram_text("First paragraph.\n\nSecond paragraph.", limit=20)
        self.assertEqual(result, ["First paragraph.", "Second paragraph."])


if __name__ == "__main__":
    unittest.main()
