import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quant_robot.config.secrets import SecretMissingError, get_env_secret, require_env_secret


class SecretTests(unittest.TestCase):
    def test_get_env_secret_reads_environment_value(self):
        with patch.dict(os.environ, {"TUSHARE_TOKEN": "token-123"}):
            self.assertEqual(get_env_secret("TUSHARE_TOKEN"), "token-123")

    def test_get_env_secret_strips_blank_values(self):
        with patch.dict(os.environ, {"TUSHARE_TOKEN": "   "}, clear=False):
            self.assertIsNone(get_env_secret("TUSHARE_TOKEN", dotenv_paths=()))

    def test_get_env_secret_reads_ignored_dotenv_when_environment_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("TUSHARE_TOKEN=dotenv-token\n", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(get_env_secret("TUSHARE_TOKEN", dotenv_paths=(env_path,)), "dotenv-token")

    def test_get_env_secret_prefers_environment_over_dotenv(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("TUSHARE_TOKEN=dotenv-token\n", encoding="utf-8")

            with patch.dict(os.environ, {"TUSHARE_TOKEN": "env-token"}, clear=True):
                self.assertEqual(get_env_secret("TUSHARE_TOKEN", dotenv_paths=(env_path,)), "env-token")

    def test_get_env_secret_parses_export_comments_and_quotes_from_dotenv(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "# local secrets",
                        "export OTHER_TOKEN=unused",
                        "export TUSHARE_TOKEN='quoted-token'",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(get_env_secret("TUSHARE_TOKEN", dotenv_paths=(env_path,)), "quoted-token")

    def test_require_env_secret_raises_clear_error(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "quant_robot.config.secrets._default_dotenv_paths", return_value=()
        ):
            with self.assertRaisesRegex(SecretMissingError, "TUSHARE_TOKEN"):
                require_env_secret("TUSHARE_TOKEN")


if __name__ == "__main__":
    unittest.main()
