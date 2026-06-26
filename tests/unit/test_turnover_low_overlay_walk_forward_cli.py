import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_turnover_low_overlay_walk_forward import run_turnover_low_overlay_walk_forward


class TurnoverLowOverlayWalkForwardCliTests(unittest.TestCase):
    def test_cli_helper_adds_market_state_policy_grid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            period_path = root / "period_returns.csv"
            market_path = root / "market_returns.csv"
            output_dir = root / "overlay"
            period_returns, market_returns = _inputs()
            period_returns.to_csv(period_path, index=False)
            market_returns.to_csv(market_path, index=False)

            result = run_turnover_low_overlay_walk_forward(
                period_returns=period_path,
                output_dir=output_dir,
                return_column="entry_cash_proxy_return",
                decision_date_column="entry_date",
                periods_per_year=252.0,
                holding_period=5,
                train_years=1,
                test_years=1,
                step_years=1,
                include_market_state_policies=True,
                market_return_csv=market_path,
                market_lookbacks=(1,),
                market_momentum_thresholds=(0.0,),
                market_cap_exposures=(0.25,),
            )

            self.assertGreater(result["summary"]["policy_count"], 6)
            self.assertTrue(any("market" in row["policy"] for row in result["policy_summary"]))
            self.assertTrue((output_dir / "turnover_low_overlay_walk_forward.json").exists())


def _inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2020-01-02", periods=760)
    period_rows = []
    market_rows = []
    for index, day in enumerate(dates):
        entry_date = day - pd.offsets.BDay(1)
        market_return = -0.03 if index % 17 == 0 else 0.004
        period_rows.append(
            {
                "date": day.date(),
                "signal_date": (entry_date - pd.offsets.BDay(1)).date(),
                "entry_date": entry_date.date(),
                "entry_cash_proxy_return": 0.003 if market_return > 0 else -0.02,
            }
        )
        market_rows.append({"date": day.date(), "market_return": market_return})
    return pd.DataFrame(period_rows), pd.DataFrame(market_rows)


if __name__ == "__main__":
    unittest.main()
