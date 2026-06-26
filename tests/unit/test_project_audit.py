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

    def test_audit_accepts_registered_etf_share_size_factor_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "walk_forward_etf_share_size.json").write_text(
                """{
  "split_date": "2024-01-01",
  "experiment_grid": {
    "factor_source": "etf_share_size",
    "factor_names": ["share_change_1d", "nav_premium_discount_low"],
    "factor_windows": [1]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

    def test_audit_accepts_registered_etf_moneyflow_basket_factor_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "walk_forward_etf_moneyflow_basket.json").write_text(
                """{
  "split_date": "2024-01-01",
  "experiment_grid": {
    "factor_source": "etf_moneyflow_basket",
    "factor_names": ["etf_net_mf_amount_ratio", "etf_net_mf_positive_weight_low"],
    "factor_windows": [1]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

    def test_audit_accepts_registered_etf_theme_breadth_factor_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "walk_forward_etf_theme_breadth.json").write_text(
                """{
  "split_date": "2024-01-01",
  "experiment_grid": {
    "factor_source": "etf_theme_breadth",
    "factor_names": ["theme_momentum_breadth_60", "theme_relative_strength_60"],
    "factor_windows": [60]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

    def test_audit_accepts_registered_cn_etf_technical_extension_factor_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "walk_forward_cn_etf_technical_extensions.json").write_text(
                """{
  "split_date": "2024-01-01",
  "experiment_grid": {
    "factor_names": [
      "trend_resilience_60",
      "market_relative_strength_60",
      "momentum_dispersion_breakout_60",
      "crash_recovery_60",
      "recovery_quality_60",
      "demand_pressure_60",
      "quiet_accumulation_60",
      "average_amount_60",
      "liquid_market_relative_strength_60",
      "liquid_crash_recovery_60",
      "liquid_recovery_quality_60",
      "liquid_demand_pressure_60",
      "liquid_quiet_accumulation_60",
      "state_adaptive_trend_defense_60",
      "state_stress_defensive_resilience_60",
      "state_stress_recovery_leadership_60"
    ],
    "factor_windows": [60]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

    def test_audit_accepts_registered_public_and_daily_basic_extension_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "experiment_public_trend_volume.json").write_text(
                """{
  "factor_source": "public_trend_volume",
  "factor_names": ["smart_money_trend_20", "anti_obv_breakout_low_tail_20"],
  "factor_windows": [20]
}
""",
                encoding="utf-8",
            )
            (root / "configs" / "experiment_daily_basic_residual_composite.json").write_text(
                """{
  "factor_source": "daily_basic_residual_composite",
  "factor_names": ["resid_value_quality_low_vol_20"],
  "factor_windows": [20]
}
""",
                encoding="utf-8",
            )
            (root / "configs" / "experiment_public_formula_price_volume.json").write_text(
                """{
  "factor_source": "public_formula_price_volume",
  "factor_names": ["formula_range_contraction_breakout_liquid_lowvol_20"],
  "factor_windows": [20]
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

    def test_audit_accepts_legacy_capacity_alias_factor_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "configs").mkdir()
            (root / "configs" / "experiment_daily_basic_legacy_aliases.json").write_text(
                """{
  "factor_source": "tushare_daily_basic",
  "factor_names": [
    "turnover_rate_low_large_mv",
    "turnover_rate_f_low_large_mv",
    "dv_ttm_mv_bucket_rank",
    "ps_ttm_inverse_mv_bucket_rank"
  ],
  "factor_windows": [1]
}
""",
                encoding="utf-8",
            )
            (root / "configs" / "walk_forward_liquid_theme_breadth_legacy_aliases.json").write_text(
                """{
  "experiment_grid": {
    "factor_source": "etf_theme_breadth",
    "factor_names": [
      "theme_relative_strength_liquid_20",
      "theme_rank_strength_liquid_20",
      "theme_risk_adjusted_strength_liquid_20"
    ],
    "factor_windows": [20]
  }
}
""",
                encoding="utf-8",
            )
            (root / "configs" / "walk_forward_high_liquidity_legacy_alias.json").write_text(
                """{
  "experiment_grid": {
    "factor_source": "technical",
    "factor_names": ["high_liquidity_20"],
    "factor_windows": [20]
  }
}
""",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            registry = audit["factor_config_registry"]
            self.assertTrue(registry["passes"])
            self.assertEqual(registry["unknown_factor_refs"], [])
            self.assertEqual(registry["unsupported_factor_sources"], [])

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
        }

        report = render_markdown_report(audit)

        self.assertIn("# Quant Robot Project Audit", report)
        self.assertIn("Safety Boundary", report)
        self.assertIn("Mock Data Boundary", report)
        self.assertIn("Factor Config Registry", report)


if __name__ == "__main__":
    unittest.main()
