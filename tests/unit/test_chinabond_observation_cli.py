import contextlib
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import capture_chinabond_observation as cli
from quant_robot.data.sources import chinabond_observation as source
from tests.unit.test_chinabond_observation import Session, page


class ChinaBondObservationCliTests(unittest.TestCase):
    def test_public_entrypoint_previews_without_network_then_archives_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as temp:
            session = Session(page())
            args = ["--machine", "office_desktop", "--branch", "codex/factor-review-example"]
            with patch.object(Path, "cwd", return_value=Path(temp)), \
                    patch.object(source, "_utc_now", return_value=datetime(2025, 1, 2, 10, 10, tzinfo=timezone.utc)), \
                    patch.object(source, "_new_session", return_value=session) as network, \
                    patch.object(cli, "run_quant_pm_startup_gate", return_value={
                        "status": "ready", "blockers": [], "primary_market": "CN_ETF"}) as gate:
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(cli.main(args), 0)
                self.assertEqual(json.loads(output.getvalue())["status"], "preview")
                network.assert_not_called()
                gate.assert_not_called()
                for _ in range(2):
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(cli.main([*args, "--execute"]), 0)
                self.assertEqual(network.call_count, 1)
                self.assertEqual(gate.call_count, 1)
                self.assertEqual(gate.call_args.kwargs["task"], "factor_review")

    def test_stale_page_and_consumed_failure_remain_nonzero(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(Path, "cwd", return_value=Path(temp)), \
                    patch.object(source, "_utc_now", return_value=datetime(2025, 1, 3, 10, 10, tzinfo=timezone.utc)), \
                    patch.object(source, "_new_session", return_value=Session(page())), \
                    patch.object(cli, "run_quant_pm_startup_gate", return_value={
                        "status": "ready", "blockers": [], "primary_market": "CN_ETF"}), \
                    contextlib.redirect_stdout(io.StringIO()):
                args = ["--machine", "office_desktop", "--branch", "codex/factor-review-example", "--execute"]
                self.assertEqual(cli.main(args), 1)
                self.assertEqual(cli.main(args), 1)


if __name__ == "__main__":
    unittest.main()
