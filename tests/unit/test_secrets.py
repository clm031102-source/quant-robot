import os
import unittest
from unittest.mock import patch

from quant_robot.config.secrets import SecretMissingError, get_env_secret, require_env_secret


class SecretTests(unittest.TestCase):
    def test_get_env_secret_reads_environment_value(self):
        with patch.dict(os.environ, {"TUSHARE_TOKEN": "token-123"}):
            self.assertEqual(get_env_secret("TUSHARE_TOKEN"), "token-123")

    def test_get_env_secret_strips_blank_values(self):
        with patch.dict(os.environ, {"TUSHARE_TOKEN": "   "}, clear=False):
            self.assertIsNone(get_env_secret("TUSHARE_TOKEN"))

    def test_require_env_secret_raises_clear_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(SecretMissingError, "TUSHARE_TOKEN"):
                require_env_secret("TUSHARE_TOKEN")


if __name__ == "__main__":
    unittest.main()
