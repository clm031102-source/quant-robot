import unittest

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from quant_robot.factors.etf_dynamic_peer_dislocation import (
    DIRECT_EXPOSURE_NAMES,
    FACTOR_NAME,
    compute_etf_dynamic_peer_dislocation,
)


class EtfDynamicPeerDislocationTests(unittest.TestCase):
    def test_matches_frozen_formula_and_direct_exposures(self) -> None:
        bars = _bars(day_count=34)
        dates = pd.DatetimeIndex(sorted(pd.to_datetime(bars["date"]).unique()))
        eligible = bars[["date", "asset_id", "market"]]
        mapping = _mapping(dates, peers=("B", "C", "D"))

        result = _compute(bars, mapping, eligible)
        expected = _expected_target_formula(bars)
        target_date = dates[-1]
        observed = result.diagnostics[
            result.diagnostics["asset_id"].eq("A")
            & pd.to_datetime(result.diagnostics["date"]).eq(target_date)
        ].iloc[0]

        self.assertAlmostEqual(float(observed["market_return"]), expected["market_return"])
        self.assertAlmostEqual(float(observed["market_beta"]), expected["market_beta"])
        self.assertAlmostEqual(float(observed["market_alpha"]), expected["market_alpha"])
        self.assertAlmostEqual(float(observed["residual"]), expected["residual"])
        self.assertAlmostEqual(float(observed["residual_sum"]), expected["residual_sum"])
        self.assertAlmostEqual(
            float(observed["peer_median_residual_sum"]),
            expected["peer_median_residual_sum"],
        )
        self.assertEqual(int(observed["peer_count"]), 3)
        self.assertAlmostEqual(float(observed["raw_dislocation"]), expected["raw_dislocation"])
        self.assertAlmostEqual(float(observed["robust_center"]), expected["robust_center"])
        self.assertAlmostEqual(float(observed["robust_scale"]), expected["robust_scale"])
        self.assertAlmostEqual(float(observed["factor_value"]), expected["factor_value"])

        factor = _value(result.factors, "A", target_date, FACTOR_NAME)
        self.assertAlmostEqual(factor, expected["factor_value"])
        self.assertEqual(
            tuple(sorted(result.direct_exposures["factor_name"].unique())),
            tuple(sorted(DIRECT_EXPOSURE_NAMES)),
        )
        self.assertTrue(
            np.isfinite(_value(result.direct_exposures, "A", target_date, "log_adv20"))
        )

    def test_current_ineligible_peer_reduces_count_and_blocks_factor(self) -> None:
        bars = _bars(day_count=34)
        dates = pd.DatetimeIndex(sorted(pd.to_datetime(bars["date"]).unique()))
        eligible = bars[["date", "asset_id", "market"]].copy()
        eligible = eligible[
            ~(
                eligible["asset_id"].eq("D")
                & pd.to_datetime(eligible["date"]).eq(dates[-1])
            )
        ]

        result = _compute(bars, _mapping(dates, peers=("B", "C", "D")), eligible)
        observed = result.diagnostics[
            result.diagnostics["asset_id"].eq("A")
            & pd.to_datetime(result.diagnostics["date"]).eq(dates[-1])
        ].iloc[0]

        self.assertEqual(int(observed["peer_count"]), 2)
        self.assertTrue(np.isnan(float(observed["raw_dislocation"])))
        self.assertTrue(np.isnan(_value(result.factors, "A", dates[-1], FACTOR_NAME)))

    def test_future_bars_and_future_mapping_do_not_change_history(self) -> None:
        bars = _bars(day_count=40)
        dates = pd.DatetimeIndex(sorted(pd.to_datetime(bars["date"]).unique()))
        cutoff = dates[33]
        baseline_bars = bars[pd.to_datetime(bars["date"]).le(cutoff)].copy()
        baseline_dates = dates[:34]
        baseline_mapping = _mapping(baseline_dates, peers=("B", "C", "D"))
        baseline = _compute(
            baseline_bars,
            baseline_mapping,
            baseline_bars[["date", "asset_id", "market"]],
        )

        future_bars = bars.copy()
        future_mask = pd.to_datetime(future_bars["date"]).gt(cutoff)
        future_bars.loc[future_mask & future_bars["asset_id"].eq("A"), "adj_close"] *= 9.0
        mapping = pd.concat(
            [
                _mapping(baseline_dates, peers=("B", "C", "D")),
                _mapping(
                    dates[34:],
                    peers=("C", "D", "E"),
                    source_end_date=cutoff,
                ),
            ],
            ignore_index=True,
        )
        observed = _compute(
            future_bars,
            mapping,
            future_bars[["date", "asset_id", "market"]],
        )
        observed_factors = observed.factors[
            pd.to_datetime(observed.factors["date"]).le(cutoff)
        ].reset_index(drop=True)

        assert_frame_equal(
            baseline.factors.reset_index(drop=True),
            observed_factors,
            check_exact=False,
            rtol=1e-12,
            atol=1e-12,
        )

    def test_robust_history_uses_prior_calendar_dates_not_prior_finite_rows(self) -> None:
        bars = _bars(day_count=34)
        dates = pd.DatetimeIndex(sorted(pd.to_datetime(bars["date"]).unique()))
        eligible = bars[["date", "asset_id", "market"]].copy()
        missing_dates = {dates[-3], dates[-5]}
        eligible = eligible[
            ~(
                eligible["asset_id"].eq("D")
                & pd.to_datetime(eligible["date"]).isin(missing_dates)
            )
        ]

        result = compute_etf_dynamic_peer_dislocation(
            bars,
            _mapping(dates, peers=("B", "C", "D")),
            eligible_keys=eligible,
            market_min_cross_section=4,
            beta_window=4,
            beta_min_observations=3,
            residual_sum_window=2,
            minimum_daily_peers=3,
            robust_scale_window=5,
            robust_scale_min_observations=4,
            residual_volatility_window=5,
            residual_volatility_min_observations=3,
            momentum_window=6,
            short_return_window=2,
            adv_window=3,
        )
        observed = result.diagnostics[
            result.diagnostics["asset_id"].eq("A")
            & pd.to_datetime(result.diagnostics["date"]).eq(dates[-1])
        ].iloc[0]

        self.assertEqual(int(observed["robust_observations"]), 3)
        self.assertTrue(np.isnan(float(observed["robust_center"])))
        self.assertTrue(np.isnan(_value(result.factors, "A", dates[-1], FACTOR_NAME)))

    def test_missing_price_is_not_forward_filled_or_bridged(self) -> None:
        bars = _bars(day_count=20)
        dates = pd.DatetimeIndex(sorted(pd.to_datetime(bars["date"]).unique()))
        missing_date = dates[10]
        next_date = dates[11]
        bars.loc[
            bars["asset_id"].eq("A") & pd.to_datetime(bars["date"]).eq(missing_date),
            "adj_close",
        ] = np.nan

        result = _compute(
            bars,
            _mapping(dates, peers=("B", "C", "D")),
            bars[["date", "asset_id", "market"]],
        )
        target = result.diagnostics[result.diagnostics["asset_id"].eq("A")].copy()
        missing_return = target.loc[
            pd.to_datetime(target["date"]).eq(missing_date), "asset_return"
        ].iloc[0]
        next_return = target.loc[
            pd.to_datetime(target["date"]).eq(next_date), "asset_return"
        ].iloc[0]

        self.assertTrue(np.isnan(float(missing_return)))
        self.assertTrue(np.isnan(float(next_return)))

    def test_materializes_only_active_mapped_target_keys(self) -> None:
        bars = _bars(day_count=24)
        dates = pd.DatetimeIndex(sorted(pd.to_datetime(bars["date"]).unique()))
        eligible = bars[
            pd.to_datetime(bars["date"]).ge(dates[5])
            & bars["asset_id"].isin(("A", "B", "C", "D"))
        ][["date", "asset_id", "market"]]

        result = _compute(bars, _mapping(dates, peers=("B", "C", "D")), eligible)

        self.assertEqual(set(result.factors["asset_id"]), {"A"})
        self.assertEqual(set(result.direct_exposures["asset_id"]), {"A"})
        self.assertEqual(set(result.adv20["asset_id"]), {"A"})
        self.assertEqual(pd.to_datetime(result.factors["date"]).min(), dates[5])
        self.assertEqual(len(result.factors), len(dates) - 5)

    def test_rejects_unexpected_mapping_method(self) -> None:
        bars = _bars(day_count=20)
        dates = pd.DatetimeIndex(sorted(pd.to_datetime(bars["date"]).unique()))
        mapping = _mapping(dates, peers=("B", "C", "D"))
        mapping["mapping_method"] = "current_theme_bucket"

        with self.assertRaisesRegex(ValueError, "mapping method"):
            _compute(bars, mapping, bars[["date", "asset_id", "market"]])


def _compute(
    bars: pd.DataFrame,
    mapping: pd.DataFrame,
    eligible: pd.DataFrame,
):
    return compute_etf_dynamic_peer_dislocation(
        bars,
        mapping,
        eligible_keys=eligible,
        market_min_cross_section=4,
        beta_window=4,
        beta_min_observations=3,
        residual_sum_window=2,
        minimum_daily_peers=3,
        robust_scale_window=5,
        robust_scale_min_observations=3,
        residual_volatility_window=5,
        residual_volatility_min_observations=3,
        momentum_window=6,
        short_return_window=2,
        adv_window=3,
    )


def _bars(*, day_count: int) -> pd.DataFrame:
    dates = pd.bdate_range("2023-01-02", periods=day_count)
    assets = ("A", "B", "C", "D", "E")
    prices = {asset: 10.0 + index for index, asset in enumerate(assets)}
    rows: list[dict[str, object]] = []
    for day_index, signal_date in enumerate(dates):
        common = 0.0025 * np.sin(day_index / 2.7) + 0.0012 * np.cos(day_index / 4.1)
        for asset_index, asset in enumerate(assets):
            loading = 0.65 + 0.11 * asset_index
            residual = 0.0014 * np.sin(day_index / (1.8 + asset_index * 0.2) + asset_index)
            residual += 0.00017 * ((day_index + 2 * asset_index) % 7 - 3)
            prices[asset] *= 1.0 + common * loading + residual
            rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset,
                    "market": "CN_ETF",
                    "adj_close": prices[asset],
                    "amount": 20_000_000.0 + asset_index * 2_000_000.0 + day_index * 10_000.0,
                }
            )
    return pd.DataFrame(rows)


def _mapping(
    dates: pd.DatetimeIndex,
    *,
    peers: tuple[str, ...],
    source_end_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    valid_from = pd.Timestamp(dates[0])
    valid_to = pd.Timestamp(dates[-1])
    source_end = source_end_date or (valid_from - pd.Timedelta(days=1))
    return pd.DataFrame(
        [
            {
                "asset_id": "A",
                "peer_asset_id": peer,
                "valid_from": valid_from,
                "valid_to": valid_to,
                "known_from": valid_from,
                "source_end_date": source_end,
                "similarity": 0.8 - rank * 0.05,
                "pair_observations": 120,
                "peer_rank": rank,
                "peer_count": len(peers),
                "mapping_method": "lagged_market_residual_correlation_topk",
                "source": "fixture",
            }
            for rank, peer in enumerate(peers, start=1)
        ]
    )


def _expected_target_formula(bars: pd.DataFrame) -> dict[str, float]:
    prices = bars.pivot(index="date", columns="asset_id", values="adj_close").sort_index()
    returns = prices.pct_change(fill_method=None)
    market = returns.median(axis=1)
    target_return = returns["A"]
    paired_target = target_return.where(target_return.notna() & market.notna())
    paired_market = market.where(target_return.notna() & market.notna())
    covariance = paired_target.rolling(4, min_periods=3).cov(paired_market)
    variance = paired_market.rolling(4, min_periods=3).var()
    beta = covariance / variance.where(variance.abs() > 1e-12)
    alpha = paired_target.rolling(4, min_periods=3).mean() - beta * paired_market.rolling(
        4, min_periods=3
    ).mean()
    residuals: dict[str, pd.Series] = {}
    betas: dict[str, pd.Series] = {}
    alphas: dict[str, pd.Series] = {}
    for asset in prices.columns:
        asset_return = returns[asset]
        left = asset_return.where(asset_return.notna() & market.notna())
        right = market.where(asset_return.notna() & market.notna())
        asset_cov = left.rolling(4, min_periods=3).cov(right)
        asset_var = right.rolling(4, min_periods=3).var()
        asset_beta = asset_cov / asset_var.where(asset_var.abs() > 1e-12)
        asset_alpha = left.rolling(4, min_periods=3).mean() - asset_beta * right.rolling(
            4, min_periods=3
        ).mean()
        betas[asset] = asset_beta.shift(1)
        alphas[asset] = asset_alpha.shift(1)
        residuals[asset] = asset_return - alphas[asset] - betas[asset] * market
    residual_sum = pd.DataFrame(residuals).rolling(2, min_periods=2).sum()
    peer_median = residual_sum[["B", "C", "D"]].median(axis=1)
    dislocation = residual_sum["A"] - peer_median
    prior = dislocation.shift(1)
    center = prior.rolling(5, min_periods=3).median()
    scale = prior.rolling(5, min_periods=3).apply(_mad, raw=True) * 1.4826
    factor = -(dislocation - center) / scale.where(scale > 1e-12)
    last = prices.index[-1]
    return {
        "market_return": float(market.loc[last]),
        "market_beta": float(beta.shift(1).loc[last]),
        "market_alpha": float(alpha.shift(1).loc[last]),
        "residual": float(residuals["A"].loc[last]),
        "residual_sum": float(residual_sum.loc[last, "A"]),
        "peer_median_residual_sum": float(peer_median.loc[last]),
        "raw_dislocation": float(dislocation.loc[last]),
        "robust_center": float(center.loc[last]),
        "robust_scale": float(scale.loc[last]),
        "factor_value": float(factor.loc[last]),
    }


def _mad(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    center = np.median(finite)
    return float(np.median(np.abs(finite - center)))


def _value(
    frame: pd.DataFrame,
    asset_id: str,
    signal_date: pd.Timestamp,
    factor_name: str,
) -> float:
    match = frame[
        frame["asset_id"].eq(asset_id)
        & pd.to_datetime(frame["date"]).eq(pd.Timestamp(signal_date))
        & frame["factor_name"].eq(factor_name)
    ]
    if len(match) != 1:
        raise AssertionError(f"Expected one {factor_name} row, found {len(match)}")
    return float(match.iloc[0]["factor_value"])


if __name__ == "__main__":
    unittest.main()
