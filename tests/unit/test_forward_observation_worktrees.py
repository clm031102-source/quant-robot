import contextlib
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import capture_chinabond_observation as bond_cli
from scripts import capture_tushare_moneyflow_observation as flow_cli
from quant_robot.data.sources import chinabond_observation as bond
from quant_robot.data.sources import tushare_moneyflow_observation as flow
from tests.unit.test_chinabond_observation import Session as BondSession, page
from tests.unit.test_tushare_moneyflow_observation import Session, Response, TOKEN, payload


class ForwardObservationWorktreeTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.primary = Path(self.temp, "primary")
        self.linked = Path(self.temp, "linked")
        self.primary.mkdir()
        self.git("init", "--quiet")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "--quiet", "--allow-empty", "-m", "fixture")
        self.git("worktree", "add", "--quiet", "--detach", str(self.linked), "HEAD")
        self.args = ["--machine", "office_desktop", "--branch", "codex/factor-review-linked"]
        self.ready = {"status": "ready", "primary_market": "CN_ETF", "blockers": []}

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.primary), *args], check=True,
                       capture_output=True, text=True)

    def invoke(self, cli, root, *, execute=True):
        with patch.object(Path, "cwd", return_value=root), contextlib.redirect_stdout(io.StringIO()) as output:
            code = cli.main([*self.args, *(["--execute"] if execute else [])])
        return code, json.loads(output.getvalue())

    def test_chinabond_worktree_and_primary_share_daily_claim_and_preview_path(self):
        with patch.object(bond, "_utc_now", return_value=datetime(2025, 1, 2, 10, 10, tzinfo=timezone.utc)), \
                patch.object(bond, "_new_session", return_value=BondSession(page())) as network, \
                patch.object(bond_cli, "run_quant_pm_startup_gate", return_value=self.ready) as gate:
            code, preview = self.invoke(bond_cli, self.linked, execute=False)
            self.assertEqual((code, preview["status"]), (0, "preview"))
            self.assertEqual(preview.get("archive_repo_root"), str(self.primary.resolve()))
            self.assertFalse((self.primary / "data").exists())
            gate.assert_not_called()
            network.assert_not_called()
            first = self.invoke(bond_cli, self.linked)[1]
            second = self.invoke(bond_cli, self.primary)[1]
        self.assertEqual(first["status"], "observed_unqualified")
        self.assertEqual(second["status"], "already_attempted")
        self.assertEqual(network.call_count, 1)
        self.assertEqual(gate.call_count, 1)
        self.assertEqual(gate.call_args.kwargs["branch"], self.args[-1])
        self.assertTrue(Path(first["record_path"]).is_relative_to(self.primary.resolve()))
        self.assertFalse((self.linked / "data").exists())

    def test_moneyflow_primary_and_worktree_share_receipts_and_failure_claims(self):
        with patch.object(flow, "_utc_now", return_value=datetime(2025, 1, 2, 11, 10, tzinfo=timezone.utc)), \
                patch.object(flow, "_new_session", return_value=Session([Response(payload()), Response(payload())])) as network, \
                patch.object(flow_cli, "require_env_secret", return_value=TOKEN) as secret, \
                patch.object(flow_cli, "run_quant_pm_startup_gate", return_value=self.ready) as gate:
            first = self.invoke(flow_cli, self.primary)[1]
            second = self.invoke(flow_cli, self.linked)[1]
            self.assertEqual(first["status"], "observed_unqualified")
            self.assertEqual(second["status"], "already_attempted")
            self.assertEqual(network.call_count, 1)
            self.assertEqual(secret.call_count, 1)
            self.assertEqual(gate.call_count, 1)
            with patch.object(flow, "_utc_now", return_value=datetime(2025, 1, 3, 11, 10, tzinfo=timezone.utc)), \
                    patch.object(flow_cli, "require_env_secret", side_effect=ValueError("missing")) as missing:
                self.assertEqual(self.invoke(flow_cli, self.linked)[0], 1)
                code, repeated = self.invoke(flow_cli, self.primary)
                self.assertEqual(code, 1)
                self.assertEqual(repeated["status"], "already_attempted")
                self.assertEqual(repeated["previous_status"], "credential_missing")
                self.assertEqual(missing.call_count, 1)
        self.assertFalse((self.linked / "data").exists())

    def test_existing_worktree_archive_is_rejected_instead_of_ignoring_its_claims(self):
        clean = Path(self.temp, "clean")
        self.git("worktree", "add", "--quiet", "--detach", str(clean), "HEAD")
        for cli, relative in ((bond_cli, "chinabond_forward_observations"), (flow_cli, "tushare_moneyflow_forward")):
            with self.subTest(source=relative):
                local = self.linked / "data/reports" / relative
                local.mkdir(parents=True)
                (local / "old-claim.json").write_text("{}", encoding="utf-8")
                with patch.object(cli, "run_quant_pm_startup_gate") as gate:
                    for workspace in (self.linked, self.primary, clean):
                        code, result = self.invoke(cli, workspace)
                        self.assertEqual((code, result["status"]), (1, "rejected"))
                gate.assert_not_called()
                self.assertFalse((self.primary / "data").exists())

    def test_broken_worktree_identity_fails_before_gate_or_credentials(self):
        broken = Path(self.temp, "broken")
        broken.mkdir()
        (broken / ".git").write_text("gitdir: missing\n", encoding="utf-8")
        with patch.object(flow_cli, "require_env_secret") as secret, \
                patch.object(flow_cli, "run_quant_pm_startup_gate") as gate:
            code, result = self.invoke(flow_cli, broken)
        self.assertEqual((code, result["status"]), (1, "rejected"))
        gate.assert_not_called()
        secret.assert_not_called()


if __name__ == "__main__":
    unittest.main()
