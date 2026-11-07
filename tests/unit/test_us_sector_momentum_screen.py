import copy
from datetime import date, datetime, timedelta
from decimal import localcontext
import json
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo

from quant_robot.research import us_sector_momentum_screen as M

ROOT = Path(__file__).resolve().parents[2]


def method():
    return json.loads((ROOT / "configs/us_sector_momentum_screen_20261107.json").read_text())


def artificial_sources():
    days = []
    d = date(2005, 1, 3)
    while d <= date(2025, 12, 31):
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += timedelta(days=1)
    def stamp(d):
        return int(datetime.fromisoformat(d).replace(hour=9, minute=30, tzinfo=ZoneInfo("America/New_York")).timestamp())
    outputs = {}
    for symbol in M.ASSETS:
        events = {}
        if symbol in method()["source_qa"]["known_true_splits"]:
            t = stamp("2025-12-05")
            events["splits"] = {str(t): dict(date=t, numerator=2, denominator=1, splitRatio="2:1")}
        if symbol == "XLF":
            t = stamp("2016-09-19")
            events["splits"] = {str(t): dict(date=t, numerator=1232, denominator=1000, splitRatio="1232:1000")}
        row = dict(meta=dict(symbol=symbol, currency="USD", instrumentType="ETF",
                            exchangeTimezoneName="America/New_York", dataGranularity="1d"),
                   timestamp=[stamp(d) for d in days], events=events,
                   indicators={"adjclose": [{"adjclose": [100.0] * len(days)}]})
        outputs[symbol] = json.dumps(dict(chart=dict(error=None, result=[row]))).encode()
    return outputs


class SectorScreenTests(unittest.TestCase):
    def test_qa_fixed_dates_tolerance_and_ambient_precision(self):
        prepared = M.inspect_sources(artificial_sources(), method())
        values = prepared["opaque_adjusted_close"]["XLF"]
        index = prepared["dates"].index("2016-09-30")
        values[index] = "108.42"
        with localcontext() as ctx:
            ctx.prec = 3
            result = M.source_qa(prepared, method())
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["absolute_difference"], "0.0100")
        values[index] = "108.4201"
        self.assertEqual(M.source_qa(prepared, method())["status"], "failed")

    def test_source_structure_does_not_convert_prices(self):
        sources = artificial_sources()
        value = json.loads(sources["XLB"])
        value["chart"]["result"][0]["indicators"]["adjclose"][0]["adjclose"][0] = None
        sources["XLB"] = json.dumps(value).encode()
        prepared = M.inspect_sources(sources, method())
        self.assertIsNone(prepared["opaque_adjusted_close"]["XLB"][0])
        with self.assertRaisesRegex(ValueError, "source_qa_must_pass"):
            M.screen(prepared, method(), {"status": "failed"})

    def test_no_intersection_no_unknown_actions_negative_ratios(self):
        original = artificial_sources()
        for mutation, reason in (("missing_date", "exact_date_sets"), ("unknown_split", "unexpected_split"),
                                 ("negative_ratio", "positive_split_parts")):
            sources = original.copy()
            value = json.loads(sources["XLB"])
            row = value["chart"]["result"][0]
            if mutation == "missing_date":
                row["timestamp"].pop(30)
                row["indicators"]["adjclose"][0]["adjclose"].pop(30)
            elif mutation == "unknown_split":
                e = next(iter(row["events"]["splits"].values()))
                e["date"] = row["timestamp"][0]
                row["events"]["splits"] = {str(e["date"]): e}
            else:
                e = next(iter(row["events"]["splits"].values()))
                e.update(numerator=-2, denominator=-1, splitRatio="-2:-1")
            sources["XLB"] = json.dumps(value).encode()
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, reason):
                M.inspect_sources(sources, method())

    def test_old_units_earn_execution_day_return_then_drift(self):
        dates = [f"2020-01-{d:02d}" for d in range(1, 7)]
        prices = {s: [100.0] * 6 for s in M.ASSETS}
        prices["XLB"] = [100, 100, 200, 400, 800, 1600]
        schedule = [dict(execution_index=1, selected=["XLB", "XLE", "XLF"]),
                    dict(execution_index=3, selected=["XLI", "XLK", "XLP"])]
        result = M.path_values(dates, prices, schedule, "top3", dict(entry=0, rebalance=0, exit=0))
        self.assertAlmostEqual(result["daily"][1]["wealth"], 4 / 3)
        self.assertAlmostEqual(result["daily"][2]["wealth"], 2)
        self.assertAlmostEqual(result["terminal_wealth"], 2)

    def test_fixed_fee_budget_even_with_same_constituents(self):
        prepared = M.inspect_sources(artificial_sources(), method())
        dates = prepared["dates"]
        prices = {s: [100.0] * len(dates) for s in M.ASSETS}
        schedule = M.decisions(dates, prices, method())
        self.assertEqual(schedule[0]["formation_start"], "2005-06-30")
        self.assertEqual(schedule[0]["selected"], ["XLB", "XLE", "XLF"])
        self.assertGreater(schedule[0]["execution_date"], schedule[0]["decision_date"])
        fees = {k: float(v) for k, v in method()["fee_proxy"]["stress"].items()}
        result = M.path_values(dates, prices, schedule, "top3", fees)
        self.assertAlmostEqual(result["terminal_wealth"], (1 - .0105) * (1 - .0215) ** 39 * (1 - .011))
        self.assertEqual(len(result["charges"]), 41)

    def test_future_prices_do_not_change_prior_rank(self):
        prepared = M.inspect_sources(artificial_sources(), method())
        dates = prepared["dates"]
        prices = {s: [100.0] * len(dates) for s in M.ASSETS}
        before = M.decisions(dates, prices, method())[0]
        for i in range(before["execution_index"], len(dates)):
            prices["XLY"][i] = 1000000.0
        after = M.decisions(dates, prices, method())[0]
        self.assertEqual(before, after)

    def test_constant_series_has_no_cost_adjusted_edge(self):
        prepared = M.inspect_sources(artificial_sources(), method())
        # Artificial QA acceptance isolates the research arithmetic, not a source claim.
        result = M.screen(prepared, method(), {"status": "passed", "artificial": True})
        self.assertEqual(result["status"], "screen_rejected")
        self.assertFalse(any(result["checks"].values()))
        self.assertAlmostEqual(result["paths"]["equal9_gross"]["terminal_wealth"], 1)
        self.assertEqual(result["account_count"], 0)
        self.assertFalse(result["qualified"])

    def test_bootstrap_known_constant_and_seed(self):
        self.assertAlmostEqual(M.bootstrap_lower([.01] * 20, seed=20261107, length=2, replications=10000), .01)


if __name__ == "__main__":
    unittest.main()
