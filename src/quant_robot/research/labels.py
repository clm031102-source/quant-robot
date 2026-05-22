from __future__ import annotations

import pandas as pd


def make_forward_returns(bars: pd.DataFrame, horizons: tuple[int, ...] = (1, 5, 20), execution_lag: int = 1) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing columns for forward returns: {', '.join(missing)}")

    rows: list[pd.DataFrame] = []
    frame = bars.sort_values(["asset_id", "date"]).copy()
    for _, group in frame.groupby("asset_id", sort=False):
        group = group.reset_index(drop=True)
        for horizon in horizons:
            entry = group["adj_close"].shift(-execution_lag)
            exit_ = group["adj_close"].shift(-(execution_lag + horizon))
            labels = pd.DataFrame(
                {
                    "date": group["date"],
                    "asset_id": group["asset_id"],
                    "market": group["market"],
                    "horizon": horizon,
                    "execution_lag": execution_lag,
                    "forward_return": exit_ / entry - 1.0,
                    "entry_date": group["date"].shift(-execution_lag),
                    "exit_date": group["date"].shift(-(execution_lag + horizon)),
                }
            )
            rows.append(labels.dropna(subset=["forward_return", "entry_date", "exit_date"]))
    if not rows:
        return pd.DataFrame(
            columns=[
                "date",
                "asset_id",
                "market",
                "horizon",
                "execution_lag",
                "forward_return",
                "entry_date",
                "exit_date",
            ]
        )
    return pd.concat(rows, ignore_index=True).sort_values(["asset_id", "date", "horizon"]).reset_index(drop=True)
