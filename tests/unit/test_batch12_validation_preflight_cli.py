import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.run_cn_stock_batch12_validation_preflight import run_cn_stock_batch12_validation_preflight
from tests.unit.test_batch12_validation_preflight import _handoff, _startup_gate


class Batch12ValidationPreflightCliTests(unittest.TestCase):
    def test_cli_runner_writes_batch12_validation_preflight_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff_path = root / "handoff.json"
            startup_gate_path = root / "startup_gate.json"
            output_dir = root / "preflight"
            handoff_path.write_text(json.dumps(_handoff()), encoding="utf-8")
            startup_gate_path.write_text(json.dumps(_startup_gate()), encoding="utf-8")

            packet = run_cn_stock_batch12_validation_preflight(
                handoff_path=handoff_path,
                startup_gate_packet=startup_gate_path,
                output_dir=output_dir,
                machine="office_desktop",
                task="factor_validation",
                branch="codex/factor-validation-cn-stock-20260617",
                current_branch="codex/factor-validation-cn-stock-20260617",
            )

            self.assertEqual(packet["status"], "cleared")
            self.assertTrue((output_dir / "batch12_validation_preflight.json").exists())
            self.assertTrue((output_dir / "batch12_validation_preflight.md").exists())
            payload = json.loads((output_dir / "batch12_validation_preflight.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["generated_at"], date.today().isoformat())
            self.assertEqual(payload["validation_window"]["start"], "2025-01-01")
            self.assertEqual(len(payload["frozen_candidates"]), 2)


if __name__ == "__main__":
    unittest.main()

