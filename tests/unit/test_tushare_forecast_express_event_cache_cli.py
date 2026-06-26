import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts.run_tushare_forecast_express_event_cache import TushareEventEndpointAdapter, main


class TushareForecastExpressEventCacheCliTests(unittest.TestCase):
    def test_live_adapter_exposes_calendar_and_generic_event_endpoint(self) -> None:
        class FakeClient:
            def forecast(self, **kwargs):
                return pd.DataFrame({"kwargs": [kwargs["start_date"]]})

        class FakeAdapter:
            client = FakeClient()

            def fetch_trade_calendar(self, start_date: str, end_date: str):
                return pd.DataFrame({"date": [start_date, end_date]})

        adapter = TushareEventEndpointAdapter(adapter=FakeAdapter())

        calendar = adapter.fetch_trade_calendar("2024-01-02", "2024-01-03")
        forecast = adapter.fetch_event_endpoint("forecast", start_date="20240101", end_date="20240131")

        self.assertEqual(len(calendar), 2)
        self.assertEqual(forecast.loc[0, "kwargs"], "20240101")

    def test_cli_defaults_to_report_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.run_tushare_forecast_express_event_cache.TushareEventEndpointAdapter") as adapter_cls:
                adapter = adapter_cls.return_value
                with patch(
                    "scripts.run_tushare_forecast_express_event_cache.run_tushare_forecast_express_event_cache",
                    return_value={"summary": {"endpoint_count": 2}},
                ) as run_cache:
                    with redirect_stdout(StringIO()):
                        exit_code = main(
                            [
                                "--start-date",
                                "2024-01-02",
                                "--end-date",
                                "2024-02-05",
                                "--output-dir",
                                tmp,
                            ]
                        )

            self.assertEqual(exit_code, 0)
            run_cache.assert_called_once()
            self.assertIs(run_cache.call_args.args[0], adapter)
            self.assertEqual(run_cache.call_args.args[1], "2024-01-02")
            self.assertEqual(run_cache.call_args.args[2], "2024-02-05")
            self.assertEqual(run_cache.call_args.args[3], Path(tmp))
            self.assertFalse(run_cache.call_args.kwargs["execute_write_processed"])

    def test_cli_requires_explicit_flag_for_processed_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.run_tushare_forecast_express_event_cache.TushareEventEndpointAdapter"):
                with patch(
                    "scripts.run_tushare_forecast_express_event_cache.run_tushare_forecast_express_event_cache",
                    return_value={"summary": {"endpoint_count": 2}},
                ) as run_cache:
                    with redirect_stdout(StringIO()):
                        exit_code = main(
                            [
                                "--start-date",
                                "2024-01-02",
                                "--end-date",
                                "2024-02-05",
                                "--output-dir",
                                tmp,
                                "--execute-write-processed",
                            ]
                        )

            self.assertEqual(exit_code, 0)
            self.assertTrue(run_cache.call_args.kwargs["execute_write_processed"])


if __name__ == "__main__":
    unittest.main()
