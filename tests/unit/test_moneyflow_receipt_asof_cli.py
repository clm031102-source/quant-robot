import contextlib
from datetime import timedelta
from decimal import Decimal
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import review_tushare_moneyflow_asof as cli
from tests.unit import test_moneyflow_receipt_asof as fixture_module
from tests.unit.test_tushare_moneyflow_observation import payload


class MoneyflowReceiptAsOfCliTests(unittest.TestCase):
    def setUp(self):
        # Reuse only the collector fixture helpers, not the reader test methods.
        self.fixture = fixture_module.MoneyflowReceiptAsOfTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root

    def invoke(self, manifest, name, *, gate=None):
        scope = self.root / (name + ".json")
        scope.write_text(json.dumps(manifest), encoding="utf-8")
        output = self.root / "data/reports" / name
        with patch.object(Path, "cwd", return_value=self.root), \
                patch.object(cli, "run_quant_pm_startup_gate", return_value=gate or {
                    "status": "ready", "primary_market": "CN_ETF", "blockers": []}) as gate_call, \
                contextlib.redirect_stdout(io.StringIO()) as printed:
            code = cli.main(["--scope", str(scope), "--output", str(output),
                "--machine", "office_desktop", "--branch", "codex/factor-review-test"])
        return code, json.loads(printed.getvalue()), output, gate_call

    def test_public_entrypoint_retains_distinct_early_and_late_results(self):
        self.fixture.capture(payload(value=10))
        self.fixture.now += timedelta(days=1)
        self.fixture.capture(payload("20250103"), payload(value=20))
        for name, cutoff, amount in [("early", "2025-01-02T11:15:00+00:00", 10),
                                     ("late", "2025-01-03T11:15:00+00:00", 20)]:
            code, summary, output, gate = self.invoke(self.fixture.manifest(cutoff), name)
            self.assertEqual(code, 0)
            self.assertTrue(summary["source_selection_complete"])
            result = json.loads((output / "result.json").read_bytes())
            self.assertEqual(Decimal(self.fixture.value(result)["net_mf_amount"]), Decimal(amount))
            self.assertFalse(result["research_admission_granted"])
            self.assertEqual(gate.call_count, 1)
            self.assertEqual(gate.call_args.kwargs["task"], "factor_review")

    def test_unknown_cells_produce_nonzero_and_review_artifact(self):
        self.fixture.capture(payload())
        code, summary, output, _ = self.invoke(self.fixture.manifest("2025-01-02T11:00:00+00:00"), "unknown")
        self.assertEqual(code, 1)
        self.assertEqual(summary["unknown_cells"], 2)
        self.assertTrue((output / "result.json").is_file())

    def test_gate_rejection_prevents_source_reader(self):
        self.fixture.capture(payload())
        with patch.object(cli, "read_moneyflow_asof") as read:
            code, summary, _, _ = self.invoke(self.fixture.manifest(), "blocked", gate={
                "status": "blocked", "primary_market": "CN_ETF", "blockers": ["scope"]})
        self.assertEqual(code, 1)
        self.assertEqual(summary["status"], "gate_blocked")
        read.assert_not_called()


if __name__ == "__main__":
    unittest.main()
