import unittest

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from quant_robot.research.dynamic_comovement_peer_source import (
    DynamicPeerPolicy,
    build_dynamic_comovement_peer_source,
    summarize_scalar_reference_overlap,
    validate_dynamic_peer_mapping,
)


class DynamicComovementPeerSourceTests(unittest.TestCase):
    def test_source_is_lagged_deterministic_and_unchanged_by_future_prices(self) -> None:
        bars, eligibility = _peer_fixture()
        policy = _test_policy()

        baseline = build_dynamic_comovement_peer_source(
            bars,
            eligibility,
            analysis_start_date="2024-01-02",
            analysis_end_date="2024-04-15",
            policy=policy,
        )
        shocked = bars.copy()
        future_mask = shocked["date"].ge(pd.Timestamp("2024-03-01"))
        shocked.loc[future_mask, "adj_close"] *= np.linspace(1.0, 3.0, int(future_mask.sum()))
        with_future_changes = build_dynamic_comovement_peer_source(
            shocked,
            eligibility,
            analysis_start_date="2024-01-02",
            analysis_end_date="2024-04-15",
            policy=policy,
        )

        self.assertFalse(baseline.mapping.empty)
        self.assertTrue(
            (
                pd.to_datetime(baseline.mapping["source_end_date"])
                < pd.to_datetime(baseline.mapping["valid_from"])
            ).all()
        )
        february = baseline.mapping[
            pd.to_datetime(baseline.mapping["valid_from"]).eq(pd.Timestamp("2024-02-01"))
        ].reset_index(drop=True)
        changed_february = with_future_changes.mapping[
            pd.to_datetime(with_future_changes.mapping["valid_from"]).eq(pd.Timestamp("2024-02-01"))
        ].reset_index(drop=True)
        assert_frame_equal(february, changed_february)

        a1 = february[february["asset_id"].eq("CN_ETF_A1")]
        self.assertEqual(a1["peer_asset_id"].tolist(), ["CN_ETF_A2", "CN_ETF_A3"])
        self.assertEqual(a1["peer_rank"].tolist(), [1, 2])
        self.assertEqual(set(february["peer_count"]), {2})

    def test_stable_synthetic_clusters_have_full_peer_set_retention(self) -> None:
        bars, eligibility = _peer_fixture()

        result = build_dynamic_comovement_peer_source(
            bars,
            eligibility,
            analysis_start_date="2024-01-02",
            analysis_end_date="2024-04-15",
            policy=_test_policy(),
        )

        self.assertGreaterEqual(len(result.stability), 1)
        self.assertTrue(result.stability["median_jaccard"].ge(0.99).all())
        self.assertTrue(result.stability["median_retention"].ge(0.99).all())
        self.assertTrue(result.snapshots["reciprocity_rate"].ge(0.99).all())

    def test_scalar_reference_overlap_detects_a_copied_topology(self) -> None:
        valid_from = pd.Timestamp("2024-04-01")
        mapping = pd.DataFrame(
            [
                {"asset_id": "A", "peer_asset_id": "B", "valid_from": valid_from},
                {"asset_id": "B", "peer_asset_id": "A", "valid_from": valid_from},
                {"asset_id": "C", "peer_asset_id": "D", "valid_from": valid_from},
                {"asset_id": "D", "peer_asset_id": "C", "valid_from": valid_from},
            ]
        )
        exposures = pd.Series({"A": 1.0, "B": 1.1, "C": 10.0, "D": 10.1})

        result = summarize_scalar_reference_overlap(
            mapping,
            valid_from=valid_from,
            exposures=exposures,
            reference_name="market_beta_120",
            max_neighbors=1,
        )

        self.assertEqual(result["selected_edges"], 4)
        self.assertEqual(result["evidence_edges"], 4)
        self.assertEqual(result["common_edges"], 4)
        self.assertEqual(result["edge_evidence_coverage"], 1.0)
        self.assertEqual(result["edge_overlap"], 1.0)

    def test_mapping_validator_rejects_overlapping_directed_edge_intervals(self) -> None:
        mapping = pd.DataFrame(
            [
                {
                    "asset_id": "A",
                    "peer_asset_id": "B",
                    "valid_from": "2024-01-02",
                    "valid_to": "2024-03-31",
                    "known_from": "2024-01-02",
                    "source_end_date": "2023-12-29",
                },
                {
                    "asset_id": "A",
                    "peer_asset_id": "B",
                    "valid_from": "2024-03-01",
                    "valid_to": "2024-06-28",
                    "known_from": "2024-03-01",
                    "source_end_date": "2024-02-29",
                },
            ]
        )

        with self.assertRaisesRegex(ValueError, "overlapping directed peer intervals"):
            validate_dynamic_peer_mapping(mapping)


def _test_policy() -> DynamicPeerPolicy:
    return DynamicPeerPolicy(
        return_window=10,
        min_asset_return_observations=8,
        market_min_cross_section=6,
        beta_min_observations=6,
        pair_min_observations=6,
        min_correlation=0.50,
        max_peers=2,
        min_peers=2,
        rebalance_months=(2, 3, 4),
        residual_volatility_window=6,
        momentum_window=6,
        short_return_window=3,
        liquidity_window=3,
    )


def _peer_fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2024-01-02", "2024-04-15")
    market = np.resize(np.array([0.002, -0.001, 0.0015, -0.0005, 0.0008]), len(dates) - 1)
    pattern = np.resize(np.array([0.010, -0.008, 0.006, -0.004, 0.007, -0.005]), len(dates) - 1)
    rows = []
    eligibility_rows = []
    assets = ["CN_ETF_A1", "CN_ETF_A2", "CN_ETF_A3", "CN_ETF_B1", "CN_ETF_B2", "CN_ETF_B3"]
    for asset_index, asset_id in enumerate(assets):
        sign = 1.0 if asset_id.startswith("CN_ETF_A") else -1.0
        returns = market + sign * pattern
        prices = np.concatenate([[100.0], 100.0 * np.cumprod(1.0 + returns)])
        for date_index, signal_date in enumerate(dates):
            rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "adj_close": prices[date_index],
                    "amount": 10_000_000.0 + asset_index * 100_000.0,
                }
            )
            eligibility_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "eligible": True,
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(eligibility_rows)


if __name__ == "__main__":
    unittest.main()
