import unittest

import pandas as pd

from scripts.run_cn_etf_external_data_unlock_review import _run_probe


class FakeAdapter:
    def fetch_etf_sh_constituents(self, **parameters):
        return pd.DataFrame(
            {
                "trade_date": [parameters["trade_date"].replace("-", "")],
                "ts_code": [parameters["ts_code"]],
                "con_code": ["600000.SH"],
                "qty": [1000],
            }
        )

    def fetch_etf_sz_constituents(self, **parameters):
        raise RuntimeError("token=must-not-leak permission denied")


class RunCnEtfExternalDataUnlockReviewTests(unittest.TestCase):
    def test_dispatches_probe_and_sanitizes_provider_failure(self):
        ready = _run_probe(
            FakeAdapter(),
            {
                "endpoint": "etf_sh_cons",
                "route": "historical_pcf",
                "required_points": 8000,
                "parameters": {"ts_code": "510050.SH", "trade_date": "2024-01-02"},
                "required_columns": ["trade_date", "ts_code", "con_code", "qty"],
            },
        )
        blocked = _run_probe(
            FakeAdapter(),
            {
                "endpoint": "etf_sz_cons",
                "route": "historical_pcf",
                "required_points": 8000,
                "parameters": {"ts_code": "159919.SZ", "trade_date": "2024-01-02"},
                "required_columns": ["trade_date", "ts_code", "con_code", "qty"],
            },
        )

        self.assertEqual(ready["status"], "probe_ready")
        self.assertEqual(blocked["status"], "permission_denied")
        self.assertNotIn("must-not-leak", str(blocked))


if __name__ == "__main__":
    unittest.main()
