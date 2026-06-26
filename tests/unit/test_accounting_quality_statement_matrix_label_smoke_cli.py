import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_accounting_quality_statement_matrix_label_smoke import (
    run_accounting_quality_statement_matrix_label_smoke_cli,
)
from tests.unit.test_accounting_quality_statement_matrix_label_smoke import (
    _bar_rows,
    _statement_rows,
    _write_bars,
    _write_statement_inputs,
)


class AccountingQualityStatementMatrixLabelSmokeCliTests(unittest.TestCase):
    def test_cli_writes_label_smoke_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement_root = root / "statement"
            bars_root = root / "bars"
            output_dir = root / "report"
            _write_statement_inputs(statement_root, _statement_rows())
            _write_bars(bars_root, _bar_rows())

            result = run_accounting_quality_statement_matrix_label_smoke_cli(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
                output_dir=output_dir,
                min_label_coverage=0.90,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output_dir / "accounting_quality_statement_matrix_label_smoke.json").exists())
            self.assertTrue((output_dir / "accounting_quality_statement_matrix_label_smoke.md").exists())
            self.assertTrue((output_dir / "accounting_quality_statement_matrix_candidate_summary.csv").exists())
            saved = json.loads((output_dir / "accounting_quality_statement_matrix_label_smoke.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["summary"]["alignment_violation_rows"], 0)

    def test_cli_blocks_when_not_ready_unless_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            statement_root = root / "statement"
            bars_root = root / "bars"
            output_dir = root / "report"
            _write_statement_inputs(statement_root, _statement_rows())
            _write_bars(bars_root, _bar_rows(end="2024-05-01"))

            with self.assertRaisesRegex(RuntimeError, "accounting quality statement matrix label smoke is not ready"):
                run_accounting_quality_statement_matrix_label_smoke_cli(
                    statement_roots=[statement_root],
                    bars_roots=[bars_root],
                    output_dir=output_dir,
                    horizons=(20,),
                    min_label_coverage=0.90,
                )

            result = run_accounting_quality_statement_matrix_label_smoke_cli(
                statement_roots=[statement_root],
                bars_roots=[bars_root],
                output_dir=output_dir,
                horizons=(20,),
                min_label_coverage=0.90,
                allow_not_ready=True,
            )
            self.assertFalse(result["summary"]["passes"])


if __name__ == "__main__":
    unittest.main()
