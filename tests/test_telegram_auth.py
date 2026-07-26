from __future__ import annotations

import hashlib
import hmac
import json
import unittest
from urllib.parse import urlencode

from web.telegram_auth import validate_init_data

BOT_TOKEN = "123456789:test-token"
NOW = 1_800_000_000


def signed_init_data(*, auth_date: int = NOW, first_name: str = "Dinula") -> str:
    values = {
        "auth_date": str(auth_date),
        "query_id": "query-123",
        "user": json.dumps(
            {
                "id": 7860454784,
                "first_name": first_name,
                "username": "student",
            },
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(values)


class TelegramAuthTests(unittest.TestCase):
    def test_accepts_valid_init_data(self) -> None:
        user = validate_init_data(
            signed_init_data(),
            BOT_TOKEN,
            max_age_seconds=86400,
            now=NOW,
        )
        self.assertEqual(user.id, 7860454784)
        self.assertEqual(user.first_name, "Dinula")
        self.assertEqual(user.username, "student")

    def test_rejects_tampered_user(self) -> None:
        tampered = signed_init_data().replace("Dinula", "Attacker")
        with self.assertRaisesRegex(ValueError, "signature"):
            validate_init_data(
                tampered,
                BOT_TOKEN,
                max_age_seconds=86400,
                now=NOW,
            )

    def test_rejects_expired_init_data(self) -> None:
        with self.assertRaisesRegex(ValueError, "expired"):
            validate_init_data(
                signed_init_data(auth_date=NOW - 90000),
                BOT_TOKEN,
                max_age_seconds=86400,
                now=NOW,
            )


if __name__ == "__main__":
    unittest.main()
