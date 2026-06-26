import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from tests.unit.test_event_factor_pit_ic_prescreen import _stock_basic, _synthetic_bars


class EventFactorPitIcPrescreenCliTests(unittest.TestCase):
    def test_cli_runner_writes_prescreen_outputs_with_injected_events(self) -> None:
        from scripts.run_event_factor_pit_ic_prescreen import run_event_factor_pit_ic_prescreen_cli

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_root = root / "processed"
            report_dir = root / "report"
            stock_basic_path = root / "stock_basic.csv"
            bars = _synthetic_bars(days=16, assets=4)
            DatasetStore(store_root).write_frame(
                bars,
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            _stock_basic(4).to_csv(stock_basic_path, index=False)
            forecast = pd.DataFrame(
                {
                    "ts_code": ["000000.SZ", "000001.SZ", "000002.SZ", "000003.SZ"] * 8,
                    "ann_date": [date.strftime("%Y%m%d") for date in pd.bdate_range("2024-01-02", periods=8) for _ in range(4)],
                    "end_date": ["20240331"] * 32,
                    "p_change_min": [0.0, 1.0, 0.0, 1.0] * 8,
                    "p_change_max": [0.0, 1.0, 0.0, 1.0] * 8,
                }
            )

            result = run_event_factor_pit_ic_prescreen_cli(
                bars_roots=[store_root],
                stock_basic_path=stock_basic_path,
                output_dir=report_dir,
                event_frames={"forecast": forecast},
                analysis_start_date="2024-01-01",
                analysis_end_date="2024-12-31",
                horizons=(1,),
                execution_lag=0,
                min_cross_section=4,
                min_ic_observations=4,
            )

            self.assertEqual(result["stage"], "event_factor_pit_ic_prescreen")
            self.assertTrue((report_dir / "event_factor_pit_ic_prescreen.json").exists())
            self.assertTrue((report_dir / "event_factor_pit_ic_prescreen.md").exists())
            self.assertTrue((report_dir / "event_factor_pit_ic_prescreen_results.csv").exists())
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])

    def test_fetch_round147_event_frames_fetches_share_unlock_and_pledge_endpoints(self) -> None:
        from quant_robot.ops.event_factor_preregistration import default_event_factor_candidate_specs
        from scripts.run_event_factor_pit_ic_prescreen import fetch_round147_event_frames

        specs = {spec.factor_name: spec for spec in default_event_factor_candidate_specs()}
        adapter = _RecordingEventAdapter()

        frames = fetch_round147_event_frames(
            adapter,
            start_year=2024,
            end_year=2024,
            max_periods=2,
            candidate_specs=(
                specs["event_share_unlock_pressure_60"],
                specs["event_pledge_ratio_relief_1q"],
            ),
        )

        self.assertIn("share_float", frames)
        self.assertIn("pledge_stat", frames)
        endpoints = [endpoint for endpoint, _ in adapter.calls]
        self.assertIn("share_float", endpoints)
        self.assertIn("pledge_stat", endpoints)
        share_kwargs = [kwargs for endpoint, kwargs in adapter.calls if endpoint == "share_float"][0]
        self.assertEqual(share_kwargs["start_date"], "20240101")
        self.assertEqual(share_kwargs["end_date"], "20241231")
        pledge_kwargs = [kwargs for endpoint, kwargs in adapter.calls if endpoint == "pledge_stat"]
        self.assertEqual(len(pledge_kwargs), 2)
        self.assertTrue(all("end_date" in kwargs for kwargs in pledge_kwargs))

    def test_load_cached_forecast_express_event_frames_normalizes_event_dates(self) -> None:
        from scripts.run_event_factor_pit_ic_prescreen import load_cached_forecast_express_event_frames

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            DatasetStore(root).write_frame(
                pd.DataFrame(
                    {
                        "event_date": ["2024-01-02"],
                        "available_date": ["2024-01-03"],
                        "asset_id": ["CN_XSHE_000001"],
                        "symbol": ["000001.SZ"],
                        "market": ["CN"],
                        "source": ["tushare_express"],
                        "end_date": ["2024-03-31"],
                        "yoy_net_profit": [12.0],
                        "diluted_roe": [3.0],
                        "total_revenue": [100.0],
                        "source_event_count": [1],
                    }
                ),
                "processed/event_express",
                {"frequency": "event", "market": "CN", "year": "2024"},
            )

            frames = load_cached_forecast_express_event_frames(
                root,
                start_year=2024,
                end_year=2024,
                endpoints=("express",),
            )

        self.assertEqual(set(frames), {"express"})
        self.assertEqual(len(frames["express"]), 1)
        self.assertIn("ann_date", frames["express"].columns)
        self.assertIn("ts_code", frames["express"].columns)
        self.assertEqual(str(frames["express"].loc[0, "ts_code"]), "000001.SZ")
        self.assertEqual(pd.Timestamp(frames["express"].loc[0, "ann_date"]).date().isoformat(), "2024-01-02")


class _RecordingEventAdapter:
    def __init__(self) -> None:
        self.calls = []

    def fetch_event_endpoint(self, endpoint, **kwargs):
        self.calls.append((endpoint, kwargs))
        if endpoint == "share_float":
            return pd.DataFrame(
                {
                    "ts_code": ["000001.SZ"],
                    "ann_date": ["20240102"],
                    "float_date": ["20240119"],
                    "float_share": [1_000_000.0],
                    "float_ratio": [1.2],
                    "share_type": ["locked"],
                }
            )
        if endpoint == "pledge_stat":
            return pd.DataFrame(
                {
                    "ts_code": ["000001.SZ"],
                    "end_date": [kwargs.get("end_date", "20240105")],
                    "pledge_ratio": [3.0],
                    "pledge_count": [1],
                    "total_share": [100.0],
                }
            )
        return pd.DataFrame()


if __name__ == "__main__":
    unittest.main()
