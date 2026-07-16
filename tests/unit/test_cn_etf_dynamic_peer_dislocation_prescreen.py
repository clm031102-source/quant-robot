import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.factors.etf_dynamic_peer_dislocation import FACTOR_NAME
from quant_robot.ops.cn_etf_dynamic_peer_dislocation_prescreen import (
    CLOSED_FAMILY_REFERENCE_NAMES,
    STAGE,
    compute_closed_family_reference_union,
    summarize_cn_etf_dynamic_peer_dislocation_prescreen,
    write_cn_etf_dynamic_peer_dislocation_prescreen,
)


class CnEtfDynamicPeerDislocationPrescreenTests(unittest.TestCase):
    def test_closed_family_reference_union_contains_exactly_39_unique_names(self) -> None:
        key = pd.DataFrame(
            [{"date": pd.Timestamp("2023-01-02"), "asset_id": "A00", "market": "CN_ETF"}]
        )
        chunks = (
            CLOSED_FAMILY_REFERENCE_NAMES[:3],
            CLOSED_FAMILY_REFERENCE_NAMES[3:11],
            CLOSED_FAMILY_REFERENCE_NAMES[11:14],
            CLOSED_FAMILY_REFERENCE_NAMES[14:27],
            CLOSED_FAMILY_REFERENCE_NAMES[27:30],
            CLOSED_FAMILY_REFERENCE_NAMES[30:],
        )
        patch_names = (
            "compute_etf_skip_momentum_factors",
            "compute_etf_price_rotation_reference_factors",
            "compute_etf_liquidity_capacity_factors",
            "compute_etf_liquidity_reference_factors",
            "compute_etf_market_residual_volatility_factors",
            "compute_etf_market_residual_volatility_references",
        )
        patchers = [
            patch(
                "quant_robot.ops.cn_etf_dynamic_peer_dislocation_prescreen." + name,
                return_value=_named_factor_rows(key, names),
            )
            for name, names in zip(patch_names, chunks, strict=True)
        ]
        for patcher in patchers:
            patcher.start()
        try:
            observed = compute_closed_family_reference_union(
                pd.DataFrame(),
                eligible_keys=key,
                evaluation_keys=key,
            )
        finally:
            for patcher in reversed(patchers):
                patcher.stop()

        self.assertEqual(len(CLOSED_FAMILY_REFERENCE_NAMES), 39)
        self.assertEqual(len(set(CLOSED_FAMILY_REFERENCE_NAMES)), 39)
        self.assertEqual(set(observed["factor_name"]), set(CLOSED_FAMILY_REFERENCE_NAMES))

    def test_closed_family_reference_union_rejects_a_missing_name(self) -> None:
        key = pd.DataFrame(
            [{"date": pd.Timestamp("2023-01-02"), "asset_id": "A00", "market": "CN_ETF"}]
        )
        with self.assertRaisesRegex(ValueError, "frozen union"):
            compute_closed_family_reference_union(
                pd.DataFrame(),
                eligible_keys=key,
                evaluation_keys=key,
                expected_names=CLOSED_FAMILY_REFERENCE_NAMES[:-1],
            )

    def test_primary_passes_all_gates_and_h20_remains_diagnostic(self) -> None:
        frames = _frames()

        result = _summarize(frames)

        self.assertEqual(result["stage"], STAGE)
        self.assertEqual(result["status"], "primary_passed_backfill_required")
        self.assertEqual(result["multiple_testing_policy"]["test_count"], 2)
        self.assertEqual(result["decision"]["family_budget"], 0.0)
        self.assertTrue(result["decision"]["primary_passed"])
        self.assertFalse(result["decision"]["walk_forward_allowed"])
        primary = _row(result, 5)
        diagnostic = _row(result, 20)
        self.assertEqual(primary["horizon_role"], "primary")
        self.assertTrue(primary["role_passed"])
        self.assertEqual(primary["blockers"], [])
        self.assertEqual(diagnostic["horizon_role"], "diagnostic_only")
        self.assertTrue(diagnostic["role_passed"])
        self.assertFalse(diagnostic["research_lead"])

    def test_positive_h20_cannot_rescue_failed_primary(self) -> None:
        frames = _frames(h5_direction=-1.0)

        result = _summarize(frames)

        self.assertEqual(result["status"], "close_family_zero_budget")
        self.assertFalse(result["decision"]["primary_passed"])
        self.assertTrue(_row(result, 20)["role_passed"])
        self.assertFalse(_row(result, 5)["role_passed"])
        self.assertEqual(result["decision"]["next_action"], "close_family_zero_budget_no_rescue")

    def test_primary_fails_when_stressed_net_spread_is_not_positive(self) -> None:
        frames = _frames(h5_scale=0.00005)

        result = _summarize(frames)
        primary = _row(result, 5)

        self.assertIn("primary_10bps_net_spread_not_positive", primary["blockers"])
        self.assertLessEqual(primary["mean_net_top_minus_bottom_10bps"], 0.0)
        self.assertEqual(result["status"], "close_family_zero_budget")

    def test_primary_fails_when_any_date_lacks_capacity(self) -> None:
        frames = _frames()
        first_date = frames["adv20"]["date"].min()
        top_assets = {"A08", "A09"}
        mask = (
            pd.to_datetime(frames["adv20"]["date"]).eq(first_date)
            & frames["adv20"]["asset_id"].isin(top_assets)
        )
        frames["adv20"].loc[mask, "adv20"] = 5_000_000.0

        result = _summarize(frames)
        primary = _row(result, 5)

        self.assertIn("primary_capacity_not_supported_every_date", primary["blockers"])
        self.assertFalse(primary["every_date_supported"])
        self.assertEqual(result["status"], "close_family_zero_budget")

    def test_primary_fails_on_direct_exposure_duplicate(self) -> None:
        frames = _frames(direct_duplicate=True)

        result = _summarize(frames)
        primary = _row(result, 5)

        self.assertIn("direct_exposure_correlation_not_strictly_below_threshold", primary["blockers"])
        self.assertGreaterEqual(primary["max_abs_direct_exposure_correlation"], 0.85)
        self.assertEqual(result["status"], "close_family_zero_budget")

    def test_missing_reference_evidence_fails_closed(self) -> None:
        frames = _frames()

        result = summarize_cn_etf_dynamic_peer_dislocation_prescreen(
            frames["factors"],
            frames["labels"],
            frames["references"],
            frames["direct_exposures"],
            frames["adv20"],
            expected_reference_names=("reference", "missing_reference"),
            direct_exposure_names=("market_beta_120",),
            **_thresholds(),
        )

        self.assertIn("historical_reference_evidence_incomplete", _row(result, 5)["blockers"])
        self.assertEqual(result["summary"]["missing_reference_names"], ["missing_reference"])

    def test_writer_is_deterministic_and_emits_all_evidence_tables(self) -> None:
        result = _summarize(_frames())
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = write_cn_etf_dynamic_peer_dislocation_prescreen(first_dir, result)
            second = write_cn_etf_dynamic_peer_dislocation_prescreen(second_dir, result)

            self.assertEqual(set(first), set(second))
            self.assertIn("turnover_cost_daily", first)
            self.assertIn("capacity_daily", first)
            self.assertIn("direct_exposure_correlations", first)
            for name in first:
                self.assertEqual(
                    Path(first[name]).read_bytes(),
                    Path(second[name]).read_bytes(),
                    msg=name,
                )


def _summarize(frames: dict[str, pd.DataFrame]) -> dict:
    return summarize_cn_etf_dynamic_peer_dislocation_prescreen(
        frames["factors"],
        frames["labels"],
        frames["references"],
        frames["direct_exposures"],
        frames["adv20"],
        expected_reference_names=("reference",),
        direct_exposure_names=("market_beta_120",),
        **_thresholds(),
    )


def _thresholds() -> dict[str, object]:
    return {
        "horizons": (5, 20),
        "primary_horizon": 5,
        "diagnostic_horizon": 20,
        "min_cross_section": 10,
        "min_ic_observations": 2,
        "min_year_ic_observations": 2,
        "min_usable_years": 1,
        "alpha": 1.0,
        "min_mean_rank_ic": 0.02,
        "min_icir": 0.0,
        "min_positive_ic_rate": 0.5,
        "min_quantile_monotonicity": 0.7,
        "max_top_quantile_turnover": 0.9,
        "min_positive_year_rate": 0.5,
        "max_abs_reference_correlation": 0.85,
        "direct_min_daily_observations": 2,
        "max_abs_direct_exposure_correlation": 0.85,
        "position_value_cny": 100_000.0,
        "max_one_way_participation_rate": 0.01,
        "one_way_costs_bps": (5.0, 10.0),
        "required_positive_net_spread_bps": 10.0,
        "diagnostic_min_mean_rank_ic": 0.0,
        "diagnostic_min_quantile_spread": 0.0,
    }


def _frames(
    *,
    h5_direction: float = 1.0,
    h5_scale: float = 0.01,
    direct_duplicate: bool = False,
) -> dict[str, pd.DataFrame]:
    dates = pd.bdate_range("2023-01-02", periods=4)
    factor_rows: list[dict[str, object]] = []
    label_rows: list[dict[str, object]] = []
    reference_rows: list[dict[str, object]] = []
    exposure_rows: list[dict[str, object]] = []
    adv_rows: list[dict[str, object]] = []
    for day_index, signal_date in enumerate(dates):
        reverse_reference = day_index % 2 == 1
        for asset_index in range(10):
            asset_id = f"A{asset_index:02d}"
            factor_value = float(asset_index)
            factor_rows.append(
                _factor_row(signal_date, asset_id, FACTOR_NAME, factor_value)
            )
            label_rows.extend(
                [
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "market": "CN_ETF",
                        "horizon": 5,
                        "forward_return": h5_direction * h5_scale * factor_value,
                    },
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "market": "CN_ETF",
                        "horizon": 20,
                        "forward_return": 0.005 * factor_value,
                    },
                ]
            )
            reference_value = float(9 - asset_index if reverse_reference else asset_index)
            reference_rows.append(
                _factor_row(signal_date, asset_id, "reference", reference_value)
            )
            exposure_value = factor_value if direct_duplicate else reference_value
            exposure_rows.append(
                _factor_row(signal_date, asset_id, "market_beta_120", exposure_value)
            )
            adv_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN_ETF",
                    "adv20": 20_000_000.0,
                }
            )
    return {
        "factors": pd.DataFrame(factor_rows),
        "labels": pd.DataFrame(label_rows),
        "references": pd.DataFrame(reference_rows),
        "direct_exposures": pd.DataFrame(exposure_rows),
        "adv20": pd.DataFrame(adv_rows),
    }


def _factor_row(
    signal_date: pd.Timestamp,
    asset_id: str,
    factor_name: str,
    factor_value: float,
) -> dict[str, object]:
    return {
        "date": signal_date,
        "asset_id": asset_id,
        "market": "CN_ETF",
        "factor_name": factor_name,
        "factor_value": factor_value,
        "lookback_window": 60,
    }


def _named_factor_rows(keys: pd.DataFrame, names: tuple[str, ...]) -> pd.DataFrame:
    rows = []
    for key in keys.itertuples(index=False):
        for index, name in enumerate(names):
            rows.append(
                _factor_row(
                    pd.Timestamp(key.date),
                    str(key.asset_id),
                    str(name),
                    float(index),
                )
            )
    return pd.DataFrame(rows)


def _row(result: dict, horizon: int) -> dict:
    matches = [row for row in result["results"] if int(row["horizon"]) == horizon]
    if len(matches) != 1:
        raise AssertionError(f"Expected one horizon {horizon} row, found {len(matches)}")
    return matches[0]


if __name__ == "__main__":
    unittest.main()
