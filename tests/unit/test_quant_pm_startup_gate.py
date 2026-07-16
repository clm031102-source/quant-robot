import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.research.pm_startup_gate import (
    build_quant_pm_startup_gate,
    load_quant_pm_gate_config,
    write_quant_pm_startup_gate,
)


class QuantPmStartupGateTests(unittest.TestCase):
    def test_gate_passes_when_required_reading_and_family_schedule_are_aligned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path in [
                "AGENTS.md",
                "configs/workstations.json",
                "docs/workstation_protocol.md",
                "README.md",
                "configs/research_family_scheduler_cn_etf.json",
                "docs/research/research_family_scheduler_2026-06-17.md",
            ]:
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(f"{path}\n", encoding="utf-8")
            gate = _gate_config()
            workstations = _workstations()
            family = _family_config(moneyflow_status="auxiliary_only", moneyflow_budget=0.0)

            pack = build_quant_pm_startup_gate(
                gate_config=gate,
                workstations_config=workstations,
                repo_root=root,
                machine="highspec_desktop",
                task="factor_batch",
                branch="codex/factor-batch-cn-etf",
                current_branch="codex/factor-batch-cn-etf",
                family_config=family,
            )

            self.assertEqual(pack["status"], "ready")
            self.assertEqual(pack["blockers"], [])
            self.assertEqual(pack["reading_summary"], {"required": 6, "read": 6, "missing": 0})

    def test_gate_blocks_when_moneyflow_selection_is_primary_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for row in _gate_config()["required_reading"]:
                target = root / row["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("ok\n", encoding="utf-8")

            pack = build_quant_pm_startup_gate(
                gate_config=_gate_config(),
                workstations_config=_workstations(),
                repo_root=root,
                machine="highspec_desktop",
                task="factor_batch",
                branch="codex/factor-batch-cn-etf",
                current_branch="codex/factor-batch-cn-etf",
                family_config=_family_config(moneyflow_status="active", moneyflow_budget=0.2),
            )

            self.assertEqual(pack["status"], "blocked")
            self.assertIn("cn_stock_moneyflow_not_auxiliary_only", pack["blockers"])
            self.assertIn("cn_stock_moneyflow_budget_not_zero", pack["blockers"])

    def test_gate_blocks_missing_required_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = build_quant_pm_startup_gate(
                gate_config=_gate_config(),
                workstations_config=_workstations(),
                repo_root=root,
                machine="highspec_desktop",
                task="factor_batch",
                branch="codex/factor-batch-cn-etf",
                current_branch="codex/factor-batch-cn-etf",
                family_config=_family_config(),
            )

            self.assertEqual(pack["status"], "blocked")
            self.assertTrue(any(blocker.startswith("required_reading_missing:") for blocker in pack["blockers"]))

    def test_gate_allows_source_repair_mode_without_unlocking_factor_batches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for row in _gate_config()["required_reading"]:
                target = root / row["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("ok\n", encoding="utf-8")

            source_repair = build_quant_pm_startup_gate(
                gate_config=_gate_config(),
                workstations_config=_workstations(),
                repo_root=root,
                machine="highspec_desktop",
                task="data_pipeline",
                branch="codex/tushare-data-pipeline",
                current_branch="codex/tushare-data-pipeline",
                family_config=_source_blocked_family_config(),
            )
            factor_batch = build_quant_pm_startup_gate(
                gate_config=_gate_config(),
                workstations_config=_workstations(),
                repo_root=root,
                machine="highspec_desktop",
                task="factor_batch",
                branch="codex/factor-batch-cn-etf",
                current_branch="codex/factor-batch-cn-etf",
                family_config=_source_blocked_family_config(),
            )

            self.assertEqual(source_repair["status"], "ready")
            self.assertEqual(source_repair["mode"], "source_repair_only")
            self.assertFalse(source_repair["safety"]["factor_batch_allowed"])
            self.assertIn("research_family_scheduler_source_repair_mode", source_repair["warnings"])
            self.assertEqual(source_repair["next_actions"][0]["action"], "repair_cn_etf_source_readiness")
            self.assertEqual(factor_batch["status"], "blocked")
            self.assertIn("research_family_scheduler_not_ready", factor_batch["blockers"])
            self.assertIn("no_primary_research_allocation", factor_batch["blockers"])

    def test_gate_allows_preregistration_only_mode_without_unlocking_factor_batches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for row in _gate_config()["required_reading"]:
                target = root / row["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("ok\n", encoding="utf-8")

            preregistration = build_quant_pm_startup_gate(
                gate_config=_gate_config(),
                workstations_config=_workstations(),
                repo_root=root,
                machine="highspec_desktop",
                task="factor_review",
                branch="codex/factor-review-dynamic-peer",
                current_branch="codex/factor-review-dynamic-peer",
                family_config=_source_ready_family_config(),
            )
            factor_batch = build_quant_pm_startup_gate(
                gate_config=_gate_config(),
                workstations_config=_workstations(),
                repo_root=root,
                machine="highspec_desktop",
                task="factor_batch",
                branch="codex/factor-batch-dynamic-peer",
                current_branch="codex/factor-batch-dynamic-peer",
                family_config=_source_ready_family_config(),
            )

            self.assertEqual(preregistration["status"], "ready")
            self.assertEqual(preregistration["mode"], "preregistration_only")
            self.assertFalse(preregistration["safety"]["factor_batch_allowed"])
            self.assertIn(
                "research_family_scheduler_preregistration_mode",
                preregistration["warnings"],
            )
            self.assertEqual(
                preregistration["next_actions"][0]["action"],
                "preregister_cn_etf_source_prescreen",
            )
            self.assertEqual(factor_batch["status"], "blocked")
            self.assertIn("research_family_scheduler_not_ready", factor_batch["blockers"])

    def test_load_and_write_gate_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "gate.json"
            config_path.write_text(json.dumps(_gate_config()), encoding="utf-8")

            loaded = load_quant_pm_gate_config(config_path)
            pack = build_quant_pm_startup_gate(
                gate_config={**loaded, "required_reading": []},
                workstations_config=_workstations(),
                repo_root=root,
                machine="highspec_desktop",
                task="factor_batch",
                branch="codex/factor-batch-cn-etf",
                current_branch="codex/factor-batch-cn-etf",
                family_config=_family_config(),
            )
            write_quant_pm_startup_gate(root / "out", pack)

            self.assertTrue((root / "out" / "quant_pm_startup_gate_pack.json").exists())
            self.assertTrue((root / "out" / "quant_pm_startup_gate_pack.md").exists())
            self.assertTrue((root / "out" / "quant_pm_required_reading.csv").exists())


def _gate_config():
    return {
        "primary_market": "CN_ETF",
        "required_reading": [
            {"path": "AGENTS.md"},
            {"path": "configs/workstations.json"},
            {"path": "docs/workstation_protocol.md"},
            {"path": "README.md"},
            {"path": "configs/research_family_scheduler_cn_etf.json"},
            {"path": "docs/research/research_family_scheduler_2026-06-17.md"},
        ],
        "direction_rules": {"final_signal_market": "CN_ETF"},
    }


def _workstations():
    return {
        "machines": {
            "highspec_desktop": {
                "allowed_tasks": ["data_pipeline", "factor_batch", "factor_validation", "factor_review"]
            }
        },
        "tasks": {
            "data_pipeline": {"branch": "codex/tushare-data-pipeline"},
            "factor_batch": {"branch": "codex/factor-batch-<topic-or-date>"},
            "factor_review": {"branch": "codex/factor-review-<topic-or-date>"},
        },
    }


def _family_config(moneyflow_status="auxiliary_only", moneyflow_budget=0.0):
    return {
        "primary_market": "CN_ETF",
        "min_active_primary_families": 1,
        "families": [
            {
                "family_id": "cn_etf_price_rotation",
                "market": "CN_ETF",
                "status": "active",
                "budget_share": 0.4,
            },
            {
                "family_id": "cn_stock_moneyflow_selection",
                "market": "CN",
                "status": moneyflow_status,
                "budget_share": moneyflow_budget,
                "failed_rounds": 3,
                "rescue_iterations": 3,
                "failure_reasons": ["capacity_limited", "oos_relative_return_failed"],
            },
        ],
    }


def _source_blocked_family_config():
    return {
        "primary_market": "CN_ETF",
        "min_active_primary_families": 3,
        "last_decision": {
            "decision": "source_blocked_no_factor_batch",
            "factor_batch_allowed": False,
        },
        "families": [
            {
                "family_id": "cn_etf_fund_structure",
                "market": "CN_ETF",
                "status": "exploratory",
                "budget_share": 0.0,
                "source_readiness_status": "blocked",
            },
            {
                "family_id": "cn_etf_peer_relative_value",
                "market": "CN_ETF",
                "status": "exploratory",
                "budget_share": 0.0,
                "metadata_readiness_status": "blocked",
            },
            {
                "family_id": "cn_stock_moneyflow_selection",
                "market": "CN",
                "status": "auxiliary_only",
                "budget_share": 0.0,
            },
        ],
    }


def _source_ready_family_config():
    config = json.loads(json.dumps(_source_blocked_family_config()))
    config["last_decision"] = {
        "decision": "source_ready_preregistration_required_no_factor_batch",
        "factor_batch_allowed": False,
    }
    return config


if __name__ == "__main__":
    unittest.main()
