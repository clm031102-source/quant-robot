"""Hand-written unitless paths; no production screen, source or account runner."""
import copy
from datetime import date, timedelta
from decimal import Decimal, Inexact, ROUND_DOWN, getcontext, localcontext
import json
import math
from pathlib import Path
import unittest

from quant_robot.research import us_sector_momentum_verification as v


def artificial_saved_fixture():
    method = json.loads((Path(__file__).resolve().parents[2] /
                         "configs/us_sector_momentum_screen_20261107.json").read_text(encoding="utf-8"))
    dates, d = [], date(2005, 1, 3)
    while d <= date(2025, 12, 31):
        if d.weekday() < 5:
            dates.append(d.isoformat())
        d += timedelta(days=1)
    # Every invented asset has the SAME price. Hence selecting any three earns
    # exactly the single index return, with only stipulated fee products differing.
    quoted = ["100" if d <= "2015-09-30" else "107.42" for d in dates]
    prices = list(map(float, quoted))
    prepared = {"dates": dates, "opaque_adjusted_close": {a: quoted[:] for a in v.ASSETS},
                "events": [], "test_injected_values": True}
    last = {d[:7]: i for i, d in enumerate(dates)}
    schedule = []
    for year in range(2005, 2026):
        for month in (6, 12):
            current = f"{year}-{month:02d}"
            if not "2005-12" <= current <= "2025-06":
                continue
            prior = f"{year-1}-12" if month == 6 else f"{year}-06"
            i, j = last[current], last[prior]
            schedule.append(dict(decision_date=dates[i], formation_start=dates[j],
                                 execution_date=dates[i+1], execution_index=i+1,
                                 selected=list(v.ASSETS[:3]),
                                 scores=dict.fromkeys(v.ASSETS, prices[i]/prices[j]-1)))
    start = schedule[0]["execution_index"]
    rebalance_dates = [r["execution_date"] for r in schedule[1:]]
    paths = {}
    fee_cases = {"top3_gross": (0, 0, 0), "equal9_gross": (0, 0, 0),
                 "top3_primary_proxy": (.004, .0085, .0045),
                 "top3_stress_proxy": (.0105, .0215, .011)}
    for name, (entry, rebalance, exit_fee) in fee_cases.items():
        rows = []
        for i in range(start, len(dates)):
            count = sum(d <= dates[i] for d in rebalance_dates)
            wealth = prices[i]/100*(1-entry)*(1-rebalance)**count
            if i == len(dates)-1:
                wealth *= 1-exit_fee
            rows.append(dict(date=dates[i], wealth=wealth))
        charges = []
        for k, event in enumerate(schedule):
            i = event["execution_index"]
            precharge = 1 if k == 0 else prices[i]/100*(1-entry)*(1-rebalance)**(k-1)
            fee = entry if k == 0 else rebalance
            charges.append(dict(date=dates[i], kind="entry" if k == 0 else "rebalance",
                                fraction=fee, index_wealth_deducted=precharge*fee))
        charges.append(dict(date=dates[-1], kind="exit", fraction=exit_fee,
                            index_wealth_deducted=prices[-1]/100*(1-entry)*(1-rebalance)**39*exit_fee))
        ends = {r["date"][:4]: r["wealth"] for r in rows}
        annual, previous = {}, 1
        for year, value in ends.items():
            annual[year], previous = value/previous-1, value
        terminal = rows[-1]["wealth"]
        elapsed = (date.fromisoformat(dates[-1])-date.fromisoformat(dates[start])).days/365.25
        paths[name] = dict(terminal_wealth=terminal, total_return=terminal-1,
                           annualized_return=terminal**(1/elapsed)-1,
                           max_drawdown=0 if entry == 0 else 1-terminal,
                           annual_returns=annual, daily=rows, charges=charges,
                           account_count=0, tradable_share_units=False)
    relative = {str(y): math.log1p(paths["top3_stress_proxy"]["annual_returns"][str(y)])
                - math.log1p(paths["equal9_gross"]["annual_returns"][str(y)])
                for y in range(2006, 2026)}
    checks = dict(stress_terminal_positive=False, positive_relative_growth_both_decades=False,
                  annual_relative_bootstrap_lower_positive=False)
    qa = dict(status="passed", start="2015-09-30", end="2016-09-30",
              adjusted_close_start="100", adjusted_close_end="107.42", provider_total_return="0.0742",
              issuer_market_total_return="0.0742", absolute_difference="0", fixed_tolerance="0.0100",
              financial_values_converted=2, qualification="coarse_major_action_omission_check_only")
    result = dict(schema="us_sector_momentum_screen_result_v1", evidence_kind="artificial_unitless_screen_fixture",
                  status="screen_rejected", paths=paths, decisions=schedule,
                  annual_log_relative_stress_vs_equal9=relative,
                  segment_log_relative_stress_vs_equal9=[math.fsum(relative[str(y)] for y in range(a,b+1))
                                                       for a,b in ((2006,2015),(2016,2025))],
                  # Fixed independent evaluation of the 20 annual fee-only log
                  # returns, Random(20261107), 10,000 two-year circular draws.
                  bootstrap_lower_mean_annual_log_relative=-0.04456917748560145,
                  checks=checks, source_qa=qa, source_actions=[],
                  unique_adjusted_close_values_decoded=9*len(dates), qualified=False,
                  real_forward_days=0, account_count=0)
    return prepared, method, result


class SectorMomentumVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared, cls.method, cls.result = artificial_saved_fixture()

    def test_hand_written_full_twenty_year_paths_and_statistics(self):
        report = v.verify(self.prepared, self.method, self.result)
        self.assertEqual(report["paths_checked"], 4)
        self.assertEqual(report["annual_values_checked"], 80)
        self.assertEqual(report["screen_status"], "screen_rejected")
        self.assertEqual(report["evidence_kind"], "artificial_unitless_screen_fixture")
        self.assertFalse(report["strategy_or_account_rerun"])

    def test_mixed_asset_period_mean_not_mean_daily_rebalancing(self):
        dates = ["2000-01-03", "2000-01-04", "2000-01-05"]
        with localcontext() as ctx:
            ctx.prec = 50
            prices = {a: list(map(Decimal, values)) for a, values in zip(v.ASSETS[:3],
                      (("100", "200", "200"), ("100", "50", "100"), ("100", "100", "50")))}
            schedule = [dict(execution_index=0, selected=list(v.ASSETS[:3]))]
            values, charges = v._period_path(dates, prices, schedule, "top3_primary_proxy")
            self.assertEqual(values[0], Decimal("0.996"))
            self.assertEqual(values[1], Decimal("1.162"))
            self.assertAlmostEqual(float(values[2]), 1.156771, places=13)
            self.assertEqual([x["kind"] for x in charges], ["entry", "exit"])

    def test_tampered_wealth_annual_and_fee_records_rejected(self):
        cases = (
            ("daily", lambda r: r["paths"]["top3_gross"]["daily"][20].update(wealth=9)),
            ("annual", lambda r: r["paths"]["top3_gross"]["annual_returns"].update({"2008": .5})),
            ("fee", lambda r: r["paths"]["top3_primary_proxy"]["charges"][1].update(fraction=0)),
            ("terminal", lambda r: r["paths"]["top3_gross"].update(terminal_wealth=2)),
        )
        for label, mutate in cases:
            with self.subTest(label=label):
                result = copy.deepcopy(self.result); mutate(result)
                with self.assertRaises(ValueError):
                    v.verify(self.prepared, self.method, result)

    def test_same_close_execution_and_wrong_tie_rank_rejected(self):
        for label in ("clock", "rank", "bool_index"):
            with self.subTest(label=label):
                result = copy.deepcopy(self.result)
                row = result["decisions"][0]
                if label == "clock": row["execution_date"] = row["decision_date"]
                elif label == "rank": row["selected"] = list(v.ASSETS[-3:])
                else: row["execution_index"] = True
                with self.assertRaises(ValueError):
                    v.verify(self.prepared, self.method, result)

    def test_qa_changed_input_or_misreported_success_rejected(self):
        altered = copy.deepcopy(self.prepared)
        altered["opaque_adjusted_close"]["XLF"][altered["dates"].index("2016-09-30")] = "100"
        with self.assertRaisesRegex(ValueError, "qa_pass"):
            v.verify(altered, self.method, self.result)
        result = copy.deepcopy(self.result); result["source_qa"]["fixed_tolerance"] = ".02"
        with self.assertRaisesRegex(ValueError, "qa_fixed_tolerance"):
            v.verify(self.prepared, self.method, result)

    def test_statistics_and_economic_outcome_cannot_be_overridden(self):
        for label in ("lower", "checks", "status", "qualification"):
            with self.subTest(label=label):
                result = copy.deepcopy(self.result)
                if label == "lower": result["bootstrap_lower_mean_annual_log_relative"] = .1
                elif label == "checks": result["checks"]["stress_terminal_positive"] = True
                elif label == "status": result["status"] = "screen_passed_requires_implementation_validation"
                else: result["qualified"] = True
                with self.assertRaises(ValueError):
                    v.verify(self.prepared, self.method, result)

    def test_decimal_precision_is_local_and_method_change_rejected(self):
        before = getcontext().copy()
        with localcontext() as ctx:
            ctx.prec = 7
            ctx.rounding = ROUND_DOWN
            ctx.traps[Inexact] = True
            flags = dict(ctx.flags)
            self.assertEqual(v.verify(self.prepared, self.method, self.result)["status"], "passed")
            self.assertEqual(ctx.prec, 7)
            self.assertEqual(ctx.rounding, ROUND_DOWN)
            self.assertTrue(ctx.traps[Inexact])
            self.assertEqual(dict(ctx.flags), flags)
        self.assertEqual(getcontext().prec, before.prec)
        changed = copy.deepcopy(self.method); changed["formation_months"] = 12
        with self.assertRaisesRegex(ValueError, "method_formation_months"):
            v.verify(self.prepared, changed, self.result)

    def test_bootstrap_fixed_positive_and_negative_constant_samples(self):
        self.assertAlmostEqual(v._bootstrap([.02]*20), .02, places=14)
        self.assertAlmostEqual(v._bootstrap([-.03]*20), -.03, places=14)


if __name__ == "__main__":
    unittest.main()
