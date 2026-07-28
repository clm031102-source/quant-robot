import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.cn_etf_external_data_unlock import (
    STAGE,
    classify_external_data_probe,
    summarize_cn_etf_external_data_unlock,
    write_cn_etf_external_data_unlock,
)


class CnEtfExternalDataUnlockTests(unittest.TestCase):
    def test_permission_denial_is_sanitized_and_blocks_pcf_route(self):
        probes = [
            classify_external_data_probe(
                endpoint="etf_sh_cons",
                route="historical_pcf",
                required_points=8000,
                error=RuntimeError("Tushare non-retryable request failure: permission denied"),
            ),
            classify_external_data_probe(
                endpoint="etf_sz_cons",
                route="historical_pcf",
                required_points=8000,
                error=RuntimeError("provider token=secret permission denied"),
            ),
        ]

        result = summarize_cn_etf_external_data_unlock(probes)

        self.assertEqual(result["stage"], STAGE)
        self.assertEqual(result["status"], "blocked_external_data_access")
        self.assertEqual(result["decision"]["next_action"], "unlock_historical_pcf_first")
        self.assertFalse(result["decision"]["factor_generation_allowed"])
        self.assertNotIn("secret", str(result))
        self.assertEqual(result["routes"]["historical_pcf"]["permission_denied_probes"], 2)

    def test_ready_probe_is_only_access_evidence_not_source_readiness(self):
        frame = pd.DataFrame(
            {
                "trade_date": ["20240102"],
                "ts_code": ["510050.SH"],
                "con_code": ["600000.SH"],
                "qty": [1000],
            }
        )
        probe = classify_external_data_probe(
            endpoint="etf_sh_cons",
            route="historical_pcf",
            required_points=8000,
            frame=frame,
            required_columns=("trade_date", "ts_code", "con_code", "qty"),
        )

        self.assertEqual(probe["status"], "probe_ready")
        self.assertEqual(probe["rows"], 1)
        self.assertFalse(probe["full_history_ready"])

    def test_writer_is_deterministic(self):
        result = summarize_cn_etf_external_data_unlock(
            [
                classify_external_data_probe(
                    endpoint="etf_sh_cons",
                    route="historical_pcf",
                    required_points=8000,
                    error=RuntimeError("permission denied"),
                )
            ]
        )
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_paths = write_cn_etf_external_data_unlock(first, result)
            second_paths = write_cn_etf_external_data_unlock(second, result)
            self.assertEqual(set(first_paths), set(second_paths))
            for name in first_paths:
                self.assertEqual(
                    Path(first_paths[name]).read_bytes(),
                    Path(second_paths[name]).read_bytes(),
                )


if __name__ == "__main__":
    unittest.main()
