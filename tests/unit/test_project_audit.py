import tempfile
import unittest
from pathlib import Path

from quant_robot.audit.project_audit import collect_project_audit, render_markdown_report


class ProjectAuditTests(unittest.TestCase):
    def test_audit_flags_order_implementation_but_allows_boundary_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "docs").mkdir()
            (root / "src" / "danger.py").write_text("def place_order(order):\n    return order\n", encoding="utf-8")
            (root / "docs" / "safety.md").write_text("No broker connection and no live trading.\n", encoding="utf-8")

            audit = collect_project_audit(root)

            self.assertFalse(audit["safety"]["passes"])
            self.assertEqual(len(audit["safety"]["forbidden_hits"]), 1)
            self.assertEqual(audit["safety"]["forbidden_hits"][0]["path"], "src/danger.py")
            self.assertEqual(audit["safety"]["boundary_mentions"], 1)

    def test_audit_allows_explicitly_disabled_live_order_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "safe.py").write_text(
                "FIELDS = ('live_order_allowed',)\n"
                "def decision():\n"
                "    return {'live_order_allowed': False}\n",
                encoding="utf-8",
            )
            (root / "src" / "unsafe.py").write_text(
                "def decision():\n"
                "    payload = {}\n"
                "    payload['live_order_allowed'] = True\n"
                "    return {'live_order_allowed': True}\n",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            hits = audit["safety"]["forbidden_hits"]
            self.assertEqual([hit["path"] for hit in hits], ["src/unsafe.py", "src/unsafe.py"])
            self.assertTrue(all(hit["pattern"] == "live_order" for hit in hits))

    def test_audit_reports_mock_boundary_files_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src" / "quant_robot" / "gui" / "fixtures").mkdir(parents=True)
            (root / "src" / "quant_robot" / "gui" / "fixtures" / "mock_data.py").write_text(
                "DATA_MODE = 'demo_fixture'\n",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            self.assertIn("src/quant_robot/gui/fixtures/mock_data.py", audit["mock_boundaries"]["mock_files"])
            self.assertTrue(audit["mock_boundaries"]["passes"])

    def test_audit_flags_walk_forward_factor_names_missing_from_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "walk_forward_bad_combo.json").write_text(
                """{
  "split_date": "2024-01-01",
  "experiment_grid": {
    "factor_source": "moneyflow_technical_combo",
    "factor_names": ["large_resid_liquidity_20", "office_only_factor_20"],
    "factor_windows": [20]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertFalse(registry["passes"])
            self.assertEqual(registry["configs_scanned"], 1)
            self.assertEqual(
                registry["unknown_factor_refs"],
                [
                    {
                        "path": "configs/walk_forward_bad_combo.json",
                        "factor_source": "moneyflow_technical_combo",
                        "factor_name": "office_only_factor_20",
                    }
                ],
            )
            self.assertFalse(audit["summary"]["passes"])

    def test_audit_accepts_registered_public_technical_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "walk_forward_public_technical.json").write_text(
                """{
  "split_date": "2024-01-01",
  "experiment_grid": {
    "factor_source": "public_technical",
    "factor_names": ["rsi_reversal_14", "donchian_position_20"],
    "factor_windows": [14, 20]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["configs_scanned"], 1)
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

    def test_audit_accepts_defensive_technical_factor_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "walk_forward_defensive_technical.json").write_text(
                """{
  "split_date": "2024-01-01",
  "experiment_grid": {
    "factor_source": "technical",
    "factor_names": ["low_volatility_20", "high_liquidity_20"],
    "factor_windows": [20]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["configs_scanned"], 1)
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

    def test_audit_accepts_registered_public_technical_liquidity_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "walk_forward_public_technical_liquidity.json").write_text(
                """{
  "split_date": "2024-01-01",
  "experiment_grid": {
    "factor_source": "public_technical_liquidity",
    "factor_names": ["rsi_reversal_liquid_14_20", "bollinger_reversal_liquid_20"],
    "factor_windows": [14, 20]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["configs_scanned"], 1)
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

    def test_audit_accepts_registered_public_technical_tail_guard_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "walk_forward_public_technical_tail_guard.json").write_text(
                """{
  "split_date": "2024-01-01",
  "experiment_grid": {
    "factor_source": "public_technical_tail_guard",
    "factor_names": ["rsi_reversal_liquid_low_tail_14_20", "bollinger_reversal_liquid_low_tail_20"],
    "factor_windows": [14, 20]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["configs_scanned"], 1)
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

    def test_audit_accepts_registered_public_trend_volume_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "walk_forward_public_trend_volume.json").write_text(
                """{
  "split_date": "2024-01-01",
  "experiment_grid": {
    "factor_source": "public_trend_volume",
    "factor_names": ["supertrend_volume_confirmed_10_3_20", "smart_money_trend_20"],
    "factor_windows": [10, 20]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["configs_scanned"], 1)
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

    def test_audit_accepts_registered_public_formula_price_volume_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "walk_forward_public_formula_price_volume.json").write_text(
                """{
  "split_date": "2024-01-01",
  "experiment_grid": {
    "factor_source": "public_formula_price_volume",
    "factor_names": ["formula_pv_corr_reversal_20", "formula_range_contraction_breakout_20"],
    "factor_windows": [20]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["configs_scanned"], 1)
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

    def test_audit_accepts_registered_daily_basic_value_liquidity_tail_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "walk_forward_daily_basic_value_tail.json").write_text(
                """{
  "split_date": "2024-01-01",
  "experiment_grid": {
    "factor_source": "daily_basic_value_liquidity_tail",
    "factor_names": ["value_liquid_low_tail_20", "dividend_value_liquid_low_tail_20"],
    "factor_windows": [20]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["configs_scanned"], 1)
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

    def test_audit_accepts_registered_daily_basic_residual_composite_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "walk_forward_daily_basic_residual_composite.json").write_text(
                """{
  "split_date": "2024-01-01",
  "experiment_grid": {
    "factor_source": "daily_basic_residual_composite",
    "factor_names": ["resid_value_quality_low_vol_20", "resid_value_reversal_low_tail_20"],
    "factor_windows": [20]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["configs_scanned"], 1)
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

    def test_audit_accepts_registered_daily_basic_smart_money_quality_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "walk_forward_daily_basic_smart_money_quality.json").write_text(
                """{
  "split_date": "2024-01-01",
  "experiment_grid": {
    "factor_source": "daily_basic_smart_money_quality",
    "factor_names": ["smart_money_quality_lowvol_20", "smart_money_efficiency_lowvol_20"],
    "factor_windows": [20]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["configs_scanned"], 1)
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

    def test_audit_accepts_registered_daily_basic_public_risk_filter_bridge_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "walk_forward_daily_basic_public_risk_filter_bridge.json").write_text(
                """{
  "split_date": "2024-01-01",
  "experiment_grid": {
    "factor_source": "daily_basic_public_risk_filter_bridge",
    "factor_names": ["risk_filter_bridge_equal_20", "risk_filter_bridge_anti_obv_weighted_20"],
    "factor_windows": [20]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["configs_scanned"], 1)
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

    def test_audit_accepts_registered_daily_basic_public_qvm_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "walk_forward_daily_basic_public_qvm.json").write_text(
                """{
  "split_date": "2024-01-01",
  "experiment_grid": {
    "factor_source": "daily_basic_public_quality_value_momentum",
    "factor_names": ["public_qvm_value_momentum_lowvol_20", "public_qvm_value_reversal_quality_20"],
    "factor_windows": [20]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["configs_scanned"], 1)
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

    def test_audit_accepts_registered_etf_theme_breadth_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "walk_forward_etf_theme_breadth.json").write_text(
                """{
  "split_date": "2024-01-01",
  "experiment_grid": {
    "factor_source": "etf_theme_breadth",
    "factor_names": ["theme_rank_strength_liquid_20", "theme_risk_adjusted_strength_liquid_60"],
    "factor_windows": [20, 60]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["configs_scanned"], 1)
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

    def test_audit_blocks_negative_shift_inside_factor_implementations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            factor_dir = root / "src" / "quant_robot" / "factors"
            factor_dir.mkdir(parents=True)
            (factor_dir / "leaky_factor.py").write_text(
                "def compute(frame):\n"
                "    return frame['adj_close'].shift(-1)\n",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            temporal = audit["temporal_safety"]
            self.assertFalse(temporal["passes"])
            self.assertEqual(
                temporal["blocking_hits"],
                [
                    {
                        "path": "src/quant_robot/factors/leaky_factor.py",
                        "line": 2,
                        "pattern": "negative_shift",
                        "text": "return frame['adj_close'].shift(-1)",
                    }
                ],
            )
            self.assertFalse(audit["summary"]["passes"])

    def test_audit_allows_forward_return_label_generation_as_label_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            label_dir = root / "src" / "quant_robot" / "research"
            label_dir.mkdir(parents=True)
            (label_dir / "labels.py").write_text(
                "def make_forward_returns(group, execution_lag):\n"
                "    entry = group['adj_close'].shift(-execution_lag)\n"
                "    exit_ = group['adj_close'].shift(-(execution_lag + 5))\n"
                "    return entry\n",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            temporal = audit["temporal_safety"]
            self.assertTrue(temporal["passes"])
            self.assertEqual(len(temporal["blocking_hits"]), 0)
            self.assertEqual(len(temporal["label_context_hits"]), 2)
            self.assertTrue(audit["summary"]["passes"])

    def test_markdown_report_contains_core_sections(self):
        audit = {
            "summary": {"passes": True, "files_scanned": 2},
            "safety": {"passes": True, "forbidden_hits": [], "boundary_mentions": 1},
            "mock_boundaries": {"passes": True, "mock_files": ["src/mock_data.py"]},
            "real_data": {"tushare_ready": False, "parquet_ready": False},
            "factor_config_registry": {
                "passes": True,
                "configs_scanned": 1,
                "unknown_factor_refs": [],
                "unsupported_factor_sources": [],
                "window_mismatches": [],
            },
            "temporal_safety": {
                "passes": True,
                "blocking_hits": [],
                "warning_hits": [],
                "label_context_hits": [],
            },
        }

        report = render_markdown_report(audit)

        self.assertIn("# Quant Robot Project Audit", report)
        self.assertIn("Safety Boundary", report)
        self.assertIn("Mock Data Boundary", report)
        self.assertIn("Factor Config Registry", report)
        self.assertIn("Temporal Safety", report)


if __name__ == "__main__":
    unittest.main()
