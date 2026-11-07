"""Artificial source projection and durable one-shot boundary checks."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

SPEC = importlib.util.spec_from_file_location("unit_feasibility_runner", Path(__file__).parents[2] / "scripts/run_us_unit_feasibility.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def fake_source(tmp_path, symbol="SPY", currency="USD", events=None, latest=999999):
    data = {"chart": {"error": None, "result": [{
        "meta": {"symbol": symbol, "currency": currency, "instrumentType": "ETF",
                 "exchangeTimezoneName": "America/New_York", "dataGranularity": "1d", "regularMarketPrice": latest},
        "timestamp": [1793889000, 1793975400],
        "indicators": {"quote": [{"close": [None, 23.456789]}], "adjclose": [{"adjclose": [1, 2]}]},
        "events": events or {},
    }]}}
    raw = M.save_raw(tmp_path / "raw.json", json.dumps(data).encode())
    receipt = M.save(tmp_path / "receipt.json", {"raw": raw, "HTTP_status": 200, "raw_complete": True})
    return {"raw": raw, "receipt": receipt}


class TestUnitFeasibilityController(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)

    def test_only_target_unadjusted_close_token_selected(self):
        token, structure = M.select_close(fake_source(self.path), "SPY")
        self.assertEqual(token, "23.456789")
        self.assertIsInstance(token, str)
        self.assertEqual(structure, {"symbol": "SPY", "date": "2026-11-06", "currency": "USD",
                                    "field": "quote.close", "selected": 1, "numeric_conversions": 0})

    def test_currency_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "identity"):
            M.select_close(fake_source(self.path, currency="HKD"), "SPY")

    def test_new_source_must_contain_exactly_one_day(self):
        with self.assertRaisesRegex(ValueError, "new_source_one_date_only"):
            M.select_close(fake_source(self.path, symbol="SPYM"), "SPYM")

    def test_target_day_action_rejected(self):
        with self.assertRaisesRegex(ValueError, "selected_date_action"):
            M.select_close(fake_source(self.path, events={"splits": {"x": {"date": 1793975400, "numerator": 2, "denominator": 1}}}), "SPY")

    def test_source_change_rejected(self):
        refs = fake_source(self.path)
        Path(refs["raw"]["path"]).write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "changed_input"):
            M.select_close(refs, "SPY")

    def test_nonstandard_json_number_rejected(self):
        with self.assertRaisesRegex(ValueError, "nonstandard_JSON_constant"):
            M.select_close(fake_source(self.path, latest=float("nan")), "SPY")

    def test_durable_claim_cannot_be_overwritten(self):
        target = self.path / "claim.json"
        ref = M.save(target, {"once": 1})
        with self.assertRaises(FileExistsError):
            M.save(target, {"once": 2})
        self.assertEqual(json.loads(M.bound(ref)), {"once": 1})

    def test_independent_verifier_detects_quantity_or_total_corruption(self):
        prices = {symbol: "50.1234" for symbol in M.SYMBOLS}
        result = M.calculate(prices)
        result["selected_closes"] = prices
        self.assertEqual(M.verify(result)["legs_checked"], 16)
        result["results"]["old_primary"]["legs"][0]["quantity"] += 1
        with self.assertRaisesRegex(ValueError, "independent_maximality"):
            M.verify(result)
        result = M.calculate(prices)
        result["selected_closes"] = prices
        result["results"]["old_primary"]["summary"]["cash_remaining_usd"] = "1000.00"
        with self.assertRaisesRegex(ValueError, "independent_cash"):
            M.verify(result)


if __name__ == "__main__":
    unittest.main()
