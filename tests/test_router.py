from __future__ import annotations

import unittest

from bot.router import Engine, route_text


class RouterTests(unittest.TestCase):
    def test_routes_equation_to_deepseek(self) -> None:
        self.assertEqual(route_text("Solve 2x = 10").engine, Engine.DEEPSEEK)

    def test_routes_sinhala_calculation_to_deepseek(self) -> None:
        self.assertEqual(route_text("මෙය ගණනය කරන්න").engine, Engine.DEEPSEEK)

    def test_routes_explanation_to_gemini(self) -> None:
        self.assertEqual(route_text("Explain photosynthesis").engine, Engine.GEMINI)


if __name__ == "__main__":
    unittest.main()
