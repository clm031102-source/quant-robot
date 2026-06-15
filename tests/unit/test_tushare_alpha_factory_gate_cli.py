import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TushareAlphaFactoryGateCliTests(unittest.TestCase):
    def test_script_entrypoint_writes_blocked_pack_without_env_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_dir = root / "gate"
            script_path = Path(__file__).resolve().parents[2] / "scripts" / "run_tushare_alpha_factory_gate.py"
            env = dict(os.environ)
            env["TUSHARE_TOKEN"] = ""

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--report-dir",
                    str(report_dir),
                    "--data-root",
                    str(root / "data"),
                    "--execute",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=env,
                cwd=root,
            )

            payload = json.loads((report_dir / "tushare_alpha_factory_gate_pack.json").read_text(encoding="utf-8"))
            serialized = json.dumps(payload, ensure_ascii=False)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("phase_6_0_tushare_alpha_factory_gate", result.stdout)
        self.assertEqual(payload["status"], "blocked_missing_readiness")
        self.assertIn("TUSHARE_TOKEN is not set", payload["decision"]["blockers"])
        self.assertEqual(payload["next_actions"][0]["action"], "set_tushare_token_env")
        self.assertNotIn(("f" * 64), serialized)
        self.assertFalse(payload["live_boundary_allowed"])


if __name__ == "__main__":
    unittest.main()
