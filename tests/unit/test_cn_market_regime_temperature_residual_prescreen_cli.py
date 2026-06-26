import tempfile
import unittest
from pathlib import Path

from tests.unit.test_cn_market_regime_temperature_residual_prescreen import _bars, _factor_inputs, _stock_basic
from scripts.run_cn_market_regime_temperature_residual_prescreen import (
    run_cn_market_regime_temperature_residual_prescreen_cli,
)


class CNMarketRegimeTemperatureResidualPrescreenCliTests(unittest.TestCase):
    def test_cli_runs_on_synthetic_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars_root = root / "bars_root" / "processed" / "bars" / "frequency=1d" / "market=CN" / "year=2020"
            factor_root = root / "factor_root" / "processed" / "factor_inputs" / "frequency=1d" / "market=CN" / "year=2020"
            stock_basic = root / "stock_basic.csv"
            output = root / "out"
            bars_root.mkdir(parents=True)
            factor_root.mkdir(parents=True)
            bars = _bars()
            bars.to_csv(bars_root / "part-00000.csv", index=False)
            _factor_inputs(bars).to_csv(factor_root / "part-00000.csv", index=False)
            _stock_basic().to_csv(stock_basic, index=False)

            result = run_cn_market_regime_temperature_residual_prescreen_cli(
                bars_roots=[root / "bars_root"],
                factor_inputs_root=root / "factor_root",
                stock_basic=stock_basic,
                output_dir=output,
                analysis_start_date="2020-01-01",
                analysis_end_date="2020-05-30",
                sample_every_n_dates=5,
                min_cross_section=2,
                min_ic_observations=2,
                min_signal_date_amount=0,
                min_industries=2,
                min_assets_per_industry=2,
            )

            self.assertEqual(result["summary"]["candidate_count"], 6)
            self.assertTrue((output / "cn_market_regime_temperature_residual_prescreen.json").exists())


if __name__ == "__main__":
    unittest.main()
