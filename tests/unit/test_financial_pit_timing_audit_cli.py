import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_financial_pit_timing_audit import run_financial_pit_timing_audit_cli
from tests.unit.test_financial_pit_timing_audit import _financial_row, _write_bars, _write_financial_rows


class FinancialPitTimingAuditCliTests(unittest.TestCase):
    def test_cli_writes_audit_packet_for_ready_financial_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            output = root / "output"
            _write_financial_rows(
                financial_root,
                pd.DataFrame([_financial_row("CN_XSHE_000001", "2024-04-30", "2024-03-31", roe=8.1)]),
            )
            _write_bars(bars_root, "CN_XSHE_000001", ["2024-05-06"])

            result = run_financial_pit_timing_audit_cli(
                financial_root=financial_root,
                bars_roots=[bars_root],
                output_dir=output,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output / "financial_pit_timing_audit.json").exists())
            self.assertTrue((output / "financial_pit_timing_audit.md").exists())
            payload = json.loads((output / "financial_pit_timing_audit.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["signal_unmapped_rows"], 0)
            self.assertFalse(payload["promotion_policy"]["profitability_claim_allowed"])

    def test_cli_raises_on_blocked_audit_without_allow_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(RuntimeError, "Financial PIT timing audit is not ready"):
                run_financial_pit_timing_audit_cli(
                    financial_root=root / "missing",
                    bars_roots=[root / "bars"],
                    output_dir=root / "output",
                )


if __name__ == "__main__":
    unittest.main()
