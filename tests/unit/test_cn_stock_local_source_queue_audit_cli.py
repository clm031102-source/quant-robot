import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from scripts.run_cn_stock_local_source_queue_audit import main


class CnStockLocalSourceQueueAuditCliTests(unittest.TestCase):
    def test_cli_writes_audit_artifacts_and_prints_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            reports = root / "reports"
            output = root / "out"
            (processed / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            (reports / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            stdout = StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--processed-root",
                        str(processed),
                        "--reports-root",
                        str(reports),
                        "--output-dir",
                        str(output),
                    ]
                )

            summary = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(summary["status"], "blocked")
            self.assertFalse(summary["decision"]["no_provider_factor_batch_allowed"])
            self.assertTrue((output / "cn_stock_local_source_queue_audit.json").exists())
            self.assertTrue((output / "cn_stock_local_source_queue_audit.md").exists())
            self.assertTrue((output / "cn_stock_local_source_queue_rows.csv").exists())


if __name__ == "__main__":
    unittest.main()
