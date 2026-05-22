from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.backtest.engine import run_factor_backtest
from quant_robot.data.normalize import normalize_ohlcv
from quant_robot.data.quality import validate_market_data
from quant_robot.factors.technical import compute_basic_factors
from quant_robot.research.groups import quantile_group_returns
from quant_robot.research.ic import compute_ic
from quant_robot.research.labels import make_forward_returns
from quant_robot.research.long_short import long_short_returns
from quant_robot.reports.plots import write_line_svg


def run_fixture_research(output_dir: Path | str = Path("data/reports/fixture_research")) -> dict[str, object]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    assets = _fixture_assets()
    bars = pd.concat([normalize_ohlcv(_raw_fixture(asset), asset, "fixture", "1d") for asset in assets], ignore_index=True)
    validate_market_data(bars)

    factors = compute_basic_factors(bars, windows=(2, 3))
    labels = make_forward_returns(bars, horizons=(1,), execution_lag=1)
    ic = compute_ic(factors, labels)
    groups = quantile_group_returns(factors, labels, quantiles=2)
    long_short = long_short_returns(factors, labels, quantiles=2)
    backtest_factors = factors[factors["factor_name"] == "momentum_2"].dropna(subset=["factor_value"])
    backtest = run_factor_backtest(backtest_factors, bars, top_n=2, cost_bps=5.0)

    _write_reports(output_path, backtest.metrics, backtest.equity_curve, ic, groups, long_short)
    return {
        "market_count": len({asset.market for asset in assets}),
        "bar_rows": int(len(bars)),
        "factor_rows": int(len(factors)),
        "label_rows": int(len(labels)),
        "ic_rows": int(len(ic)),
        "metrics": backtest.metrics,
    }


def _fixture_assets() -> list[Asset]:
    return [
        Asset("CN_XSHG_600519", "600519", "CN", "XSHG", "stock", "CNY", "Asia/Shanghai", "XSHG"),
        Asset("HK_XHKG_0700", "0700.HK", "HK", "XHKG", "stock", "HKD", "Asia/Hong_Kong", "XHKG"),
        Asset("US_XNAS_AAPL", "AAPL", "US", "XNAS", "stock", "USD", "America/New_York", "XNYS"),
        Asset("CRYPTO_BINANCE_BTC_USDT", "BTC/USDT", "CRYPTO", "BINANCE", "crypto_spot", "USDT", "UTC", "24/7"),
    ]


def _raw_fixture(asset: Asset) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=8)
    base_prices = {
        "CN": [100, 101, 102, 103, 105, 106, 107, 109],
        "HK": [50, 49, 50, 52, 51, 53, 54, 55],
        "US": [200, 202, 204, 208, 212, 216, 220, 224],
        "CRYPTO": [30000, 30300, 30100, 30900, 31500, 31800, 33000, 33600],
    }
    closes = pd.Series(base_prices[asset.market], dtype=float)
    volumes = pd.Series([1000, 1100, 1050, 1200, 1250, 1300, 1280, 1350], dtype=float)
    return pd.DataFrame(
        {
            "date": dates.date,
            "open": closes * 0.99,
            "high": closes * 1.02,
            "low": closes * 0.98,
            "close": closes,
            "adj_close": closes,
            "volume": volumes,
            "amount": closes * volumes,
        }
    )


def _write_reports(
    output_path: Path,
    metrics: dict[str, float],
    equity_curve: pd.DataFrame,
    ic: pd.DataFrame,
    groups: pd.DataFrame,
    long_short: pd.DataFrame,
) -> None:
    (output_path / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    equity_curve.to_csv(output_path / "equity_curve.csv", index=False)
    ic.to_csv(output_path / "ic.csv", index=False)
    groups.to_csv(output_path / "group_returns.csv", index=False)
    long_short.to_csv(output_path / "long_short.csv", index=False)
    write_line_svg(equity_curve, "date", "equity", output_path / "equity_curve.svg", "Fixture Backtest Equity")
    write_line_svg(ic, "date", "ic", output_path / "ic.svg", "Fixture Factor IC")


def main() -> None:
    result = run_fixture_research()
    print(json.dumps(result["metrics"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
