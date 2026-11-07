"""Artificial Yahoo-shaped bytes only; no source files, strategy run or network."""
from datetime import date, datetime, timedelta
from decimal import getcontext, setcontext, Inexact
import json
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from quant_robot.research import us_low_unit_allocation_inputs as m


def stamp(day, hour=9, minute=30):
    return str(int(datetime.fromisoformat(day).replace(hour=hour, minute=minute,
                                                      tzinfo=ZoneInfo("America/New_York")).timestamp()))


def packet(symbol, dates, *, monthly=False):
    prices = ["40" if symbol == "GLDM" else "100" for _ in dates]
    if "2022-09-19" in dates and symbol == "GLDM":
        prices[dates.index("2022-09-19")] = "33.26"
    quote = {f: prices.copy() for f in ("open", "high", "low", "close")}
    quote["volume"] = ["100000" for _ in dates]
    row = dict(meta=dict(symbol=symbol, currency="USD", instrumentType="ETF",
                        exchangeTimezoneName="America/New_York", dataGranularity="1mo" if monthly else "1d",
                        regularMarketPrice="NEVER_CONVERT_CURRENT_PRICE"),
               timestamp=[stamp(d, 0, 0) if monthly else stamp(d) for d in dates],
               indicators={"quote": [quote], "adjclose": [{"adjclose": ["NEVER_CONVERT_ADJCLOSE"]*len(dates)}]},
               events={})
    if symbol == "GLDM" and (monthly or "2022-02-23" in dates):
        key = stamp("2022-02-01", 0, 0) if monthly else stamp("2022-02-23")
        row["events"]["splits"] = {key: dict(date=stamp("2022-02-23"), numerator="1.0", denominator="2.0", splitRatio="1:2")}
    if monthly:
        row["indicators"]["quote"] = [{"open": ["SEALED_2026_QUOTE"]}]
    return {"chart": {"result": [row], "error": None}}


def encoded(obj):
    return json.dumps(obj, separators=(",", ":")).encode()


def changed(payloads, role, mutate):
    answer = dict(payloads)
    obj = json.loads(answer[role]); mutate(obj["chart"]["result"][0])
    answer[role] = encoded(obj)
    return answer


class SourceAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d = date(2020, 12, 1); days = []
        while d <= date(2025, 12, 31):
            if d.weekday() < 5: days.append(d.isoformat())
            d += timedelta(days=1)
        cls.dates = days
        cls.payloads = {}
        for symbol in m.SYMBOLS:
            if symbol in m.OLD:
                cls.payloads[f"{symbol}_legacy"] = encoded(packet(symbol, [x for x in days if x <= "2024-12-31"]))
                cls.payloads[f"{symbol}_2025"] = encoded(packet(symbol, [x for x in days if x >= "2025-01-01"]))
            else:
                cls.payloads[f"{symbol}_daily"] = encoded(packet(symbol, days))
            cls.payloads[f"{symbol}_actions"] = encoded(packet(symbol, ["2022-02-01", "2026-11-01"], monthly=True))

    def test_prepare_is_opaque_and_identity_dates_exact(self):
        with patch.object(m, "_number", side_effect=AssertionError("premature numeric")):
            p = m.prepare_sources(self.payloads)
            summary = m.metadata_summary(p)
        self.assertEqual(summary["dates"], self.dates)
        self.assertEqual(summary["first_decision_date"], "2020-12-31")
        self.assertEqual(len(summary["source_refs"]), 16)
        self.assertEqual(summary["blockers"], [])
        self.assertNotIn("NEVER_CONVERT", json.dumps(summary))
        self.assertNotIn("40", repr(p))
        summary["dates"].clear()
        self.assertEqual(m.metadata_summary(p)["dates"], self.dates)

    def test_fixed_qa_cache_units_capacity_and_terminal(self):
        payloads = changed(self.payloads, "GLDM_daily", lambda r: [r["indicators"]["quote"][0][f].__setitem__(-1, "SEALED_TERMINAL")
                                                                   for f in ("high", "low", "close", "volume")])
        p = m.prepare_sources(payloads)
        with patch.object(m, "_number", wraps=m._number) as convert:
            qa = m.run_unit_qa(p)
            self.assertEqual(convert.call_count, 5)
            self.assertEqual(qa["status"], "passed")
            self.assertEqual(qa["absolute_return_gap"], "0")
            self.assertEqual(qa["restored_closes"][0]["close"], "20.0")
            convert.reset_mock()
            fixtures = m.build_fixtures(p, {"constructed_from_market_data": False, "test_injected_values": True})
            self.assertEqual(convert.call_count, (len(self.dates)-1)*6*5 + 6 - 5)
        new = fixtures["new"]
        before = new["days"][self.dates.index("2022-02-22")]
        after = new["days"][self.dates.index("2022-02-23")]
        self.assertEqual(before["prices"]["GLDM"]["close"], "20.0")
        self.assertEqual(after["prices"]["GLDM"]["close"], "40")
        self.assertEqual(before["capacity_volume"]["GLDM"], "100000")
        self.assertEqual(before["prices"]["GLDM"]["volume"], "100000")
        self.assertEqual(new["splits"][0]["denominator"], 2)
        self.assertEqual(fixtures["old"]["splits"], [])
        self.assertEqual(new["evidence_kind"], "artificial_values_true_calendar")
        self.assertTrue(all(v is None for k, v in new["days"][-1]["prices"]["GLDM"].items() if k != "open"))
        self.assertIsNone(new["days"][-1]["capacity_volume"]["GLDM"])
        self.assertIsNone(new["days"][0]["execution"]["GLDM"]["suspended"])
        with self.assertRaisesRegex(ValueError, "QA_already"):
            m.run_unit_qa(p)
        with self.assertRaisesRegex(ValueError, "fixtures_already"):
            m.build_fixtures(p, {"constructed_from_market_data": False})

    def test_failed_qa_has_no_adaptive_multiplier_or_fixture(self):
        def bad(r):
            i = [m._day(x) for x in r["timestamp"]].index("2022-09-19")
            r["indicators"]["quote"][0]["close"][i] = "66.52"
        p = m.prepare_sources(changed(self.payloads, "GLDM_daily", bad))
        self.assertEqual(m.run_unit_qa(p)["status"], "failed")
        with self.assertRaisesRegex(ValueError, "passed_QA"):
            m.build_fixtures(p, {"constructed_from_market_data": False})
        with self.assertRaisesRegex(ValueError, "QA_already"):
            m.run_unit_qa(p)

    def test_unsupported_actions_are_metadata_blockers_not_guessed(self):
        def forward_split(r):
            key = stamp("2026-11-01", 0, 0)
            r["events"]["splits"] = {key: dict(date=stamp("2026-11-02"), numerator="2", denominator="1", splitRatio="2:1")}
        variants = [changed(self.payloads, "SPY_actions", forward_split),
            changed(self.payloads, "GLDM_actions", lambda r: r["events"].update(dividends={stamp("2026-11-02"): {"amount": "SEALED", "date": stamp("2026-11-02")}})),
            changed(self.payloads, "SPYM_daily", lambda r: r["events"].update(capitalGains={"x": {"amount": "SEALED"}})),
            changed(self.payloads, "GLDM_daily", lambda r: r["events"].pop("splits"))]
        for payloads in variants:
            with self.subTest(variant=variants.index(payloads)):
                p = m.prepare_sources(payloads)
                self.assertTrue(m.metadata_summary(p)["blockers"])
                with patch.object(m, "_number", side_effect=AssertionError("numeric")):
                    with self.assertRaisesRegex(ValueError, "unsupported_source_actions"):
                        m.run_unit_qa(p)

    def test_roles_json_identity_and_daily_date_gap_rejected(self):
        bad = dict(self.payloads); bad.pop("SPY_legacy")
        with self.assertRaisesRegex(ValueError, "sixteen"):
            m.prepare_sources(bad)
        for raw in (b'{"chart":1,"chart":2}', b'{"chart":NaN}'):
            bad = dict(self.payloads); bad["SPY_legacy"] = raw
            with self.assertRaises(ValueError): m.prepare_sources(bad)
        for field, value in (("currency", "CNY"), ("symbol", "SPLG"), ("dataGranularity", "1wk"), ("instrumentType", "EQUITY")):
            bad = changed(self.payloads, "SPYM_daily", lambda r: r["meta"].update({field: value}))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "source_identity"):
                m.prepare_sources(bad)
        def gap(r):
            r["timestamp"].pop(25)
            for a in r["indicators"]["quote"][0].values(): a.pop(25)
        with self.assertRaisesRegex(ValueError, "six_date_sets"):
            m.prepare_sources(changed(self.payloads, "GLD_2025", gap))

    def test_pre_window_values_opaque_dividend_window_and_old_split(self):
        def older(r):
            r["timestamp"].insert(0, stamp("2005-06-09"))
            for a in r["indicators"]["quote"][0].values(): a.insert(0, "SEALED_OLD")
            r["events"]["splits"] = {stamp("2005-06-09"): dict(date=stamp("2005-06-09"), numerator="3.0", denominator="1.0", splitRatio="3:1")}
            r["events"]["dividends"] = {stamp("2020-12-15"): dict(date=stamp("2020-12-15"), amount="SEALED_WARMUP"),
                stamp("2021-01-15"): dict(date=stamp("2021-01-15"), amount="0.2")}
        payloads = changed(self.payloads, "EFA_legacy", older)
        p = m.prepare_sources(payloads)
        self.assertEqual(len(m.metadata_summary(p)["dividend_events"]), 1)
        m.run_unit_qa(p)
        result = m.build_fixtures(p, {"constructed_from_market_data": False})
        self.assertEqual(result["old"]["dividends"][0]["amount_per_share"], "0.2")
        self.assertEqual(result["new"]["dividends"], result["old"]["dividends"])

    def test_bad_numeric_rectangle_and_mutation_fail_closed(self):
        p = m.prepare_sources(self.payloads)
        with self.assertRaisesRegex(ValueError, "passed_QA"):
            m.build_fixtures(p, {"constructed_from_market_data": False})
        p._tokens["SPY"][m.START] = ("1",)*5
        with self.assertRaisesRegex(ValueError, "prepared_input_changed"):
            m.run_unit_qa(p)
        for value in ("NaN", "Infinity", "0", "-1"):
            def change(r):
                i = [m._day(x) for x in r["timestamp"]].index("2022-02-22")
                r["indicators"]["quote"][0]["close"][i] = value
            with self.subTest(value=value):
                p = m.prepare_sources(changed(self.payloads, "GLDM_daily", change))
                with self.assertRaises(ValueError): m.run_unit_qa(p)
                with self.assertRaisesRegex(ValueError, "QA_already"): m.run_unit_qa(p)
        p = m.prepare_sources(changed(self.payloads, "SPYM_daily", lambda r: r["indicators"]["quote"][0]["low"].__setitem__(0, "200")))
        m.run_unit_qa(p)
        with self.assertRaisesRegex(ValueError, "OHLC_rectangle"):
            m.build_fixtures(p, {"constructed_from_market_data": False})

    def test_decimal_context_isolated_even_on_bad_string(self):
        saved = getcontext().copy()
        try:
            getcontext().prec = 2; getcontext().traps[Inexact] = True
            getcontext().clear_flags(); before = getcontext().copy()
            p = m.prepare_sources(self.payloads)
            self.assertEqual(m.run_unit_qa(p)["status"], "passed")
            m.build_fixtures(p, {"constructed_from_market_data": False})
            self.assertEqual(getcontext().prec, before.prec)
            self.assertEqual(getcontext().flags, before.flags)
            self.assertEqual(getcontext().traps, before.traps)
        finally:
            setcontext(saved)


if __name__ == "__main__":
    unittest.main()
