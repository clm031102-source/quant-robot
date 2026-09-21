"""Source-only implementation-notice reads; no signal or return calculation."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from quant_robot.data.sources.tushare_http import TushareSourceError, TushareSourceHttpClient
from tests.unit.test_tushare_source_http import Response, Session
from tests.unit import test_tushare_source_collection as collection_fixtures


FIELDS = "ts_code,end_date,ann_date,imp_ann_date,div_proc,record_date,ex_date,pay_date,cash_div,cash_div_tax,base_date,base_share"
ROW = ["000001.SZ", "20221231", "20230308", "20230607", "实施", "20230613", "20230614", "20230614", None, 0.285, None, 1940591.8198]


class DividendSourceTests(unittest.TestCase):
    def client(self):
        return TushareSourceHttpClient(token="private-test-token", max_requests=1, max_date="20241231")

    def request(self):
        return {"api_name": "dividend", "fields": FIELDS, "max_rows": 4,
            "ts_code": "000001.SZ", "imp_ann_date": "20230607"}

    def test_separates_proposal_from_implementation_and_preserves_unknowns(self):
        payload = {"code": 0, "data": {"fields": FIELDS.split(","), "items": [ROW, ROW], "has_more": False}}
        client = self.client()
        with patch("quant_robot.data.sources.tushare_http._new_session", return_value=Session(Response(payload))):
            frame = client.query(**self.request())
        self.assertEqual(len(frame), 2)
        self.assertEqual(client.last_payload, payload)
        self.assertNotEqual(frame.loc[0, "ann_date"], frame.loc[0, "imp_ann_date"])
        self.assertIsNone(client.last_payload["data"]["items"][0][8])

    def test_requires_single_stock_and_implementation_date_without_network(self):
        variants = []
        for symbol in (None, "", "000001.SZ,600036.SH", "510300.SH", "000001.SH"):
            req = self.request()
            if symbol is None:
                del req["ts_code"]
            else:
                req["ts_code"] = symbol
            variants.append(req)
        for replacement in ({"ann_date": "20230308"}, {"end_date": "20221231"},
                {"start_date": "20230101", "end_date": "20231231"}, {"pay_date": "20230614"}):
            req = self.request()
            del req["imp_ann_date"]
            req.update(replacement)
            variants.append(req)
        with patch("quant_robot.data.sources.tushare_http._new_session") as network:
            for req in variants:
                client = self.client()
                with self.subTest(req=req), self.assertRaises(TushareSourceError):
                    client.query(**req)
                self.assertEqual(client.requests_used, 0)
        network.assert_not_called()

    def test_required_event_fields_cannot_be_omitted(self):
        client = self.client()
        with patch("quant_robot.data.sources.tushare_http._new_session") as network:
            for name in FIELDS.split(","):
                req = self.request()
                req["fields"] = ",".join(f for f in FIELDS.split(",") if f != name)
                with self.subTest(name=name), self.assertRaises(TushareSourceError):
                    client.query(**req)
        network.assert_not_called()

    def test_all_disclosed_dates_respect_ceiling_even_if_implementation_is_old(self):
        for field in ("end_date", "ann_date", "record_date", "ex_date", "pay_date", "base_date", "div_listdate"):
            fields = FIELDS.split(",")
            row = list(ROW)
            if field not in fields:
                fields.append(field)
                row.append("20260101")
            else:
                row[fields.index(field)] = "20260101"
            payload = {"code": 0, "data": {"fields": fields, "items": [row]}}
            req = self.request()
            req["fields"] = ",".join(fields)
            client = self.client()
            with self.subTest(field=field), patch("quant_robot.data.sources.tushare_http._new_session", return_value=Session(Response(payload))):
                with self.assertRaises(TushareSourceError):
                    client.query(**req)
            self.assertIsNone(client.last_payload)

    def test_wrong_implementation_or_symbol_cannot_enter_source_projection(self):
        for column, value in ((0, "600036.SH"), (3, "20230608"), (3, None)):
            row = list(ROW)
            row[column] = value
            payload = {"code": 0, "data": {"fields": FIELDS.split(","), "items": [row]}}
            client = self.client()
            with self.subTest(column=column, value=value), patch("quant_robot.data.sources.tushare_http._new_session", return_value=Session(Response(payload))):
                with self.assertRaises(TushareSourceError):
                    client.query(**self.request())
            self.assertIsNone(client.last_payload)

    def test_source_can_retain_missing_payment_date_without_asserting_no_event(self):
        row = list(ROW)
        row[7] = None
        row[4] = "未知"
        client = self.client()
        payload = {"code": 0, "data": {"fields": FIELDS.split(","), "items": [row]}}
        with patch("quant_robot.data.sources.tushare_http._new_session", return_value=Session(Response(payload))):
            client.query(**self.request())
        self.assertEqual(client.last_payload, payload)


class DividendCollectionTests(unittest.TestCase):
    def test_frozen_collection_keeps_both_dates_and_consumes_request_once(self):
        fixture = collection_fixtures.TushareSourceCollectionTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        scope = copy.deepcopy(fixture.scope)
        req = DividendSourceTests().request()
        scope["requests"] = [{"api_name": req["api_name"], "fields": req["fields"], "max_rows": req["max_rows"],
            "params": {"ts_code": req["ts_code"], "imp_ann_date": req["imp_ann_date"]}}]
        preview = fixture.collect(scope)
        payload = {"code": 0, "data": {"fields": FIELDS.split(","), "items": [ROW], "has_more": False}}
        session = Session(Response(payload))
        with patch("quant_robot.data.sources.tushare_http._new_session", return_value=session):
            result = fixture.collect(scope, execute=True, expected_scope_sha256=preview["scope_sha256"])
            with self.assertRaisesRegex(ValueError, "already"):
                fixture.collect(scope, execute=True, expected_scope_sha256=preview["scope_sha256"])
        self.assertEqual(result["status"], "collected_unqualified")
        self.assertFalse(result["source_audit_verified"])
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(json.loads((Path(result["output_dir"]) / "response_001.json").read_text()), payload)

    def test_explicit_market_day_scope_collects_one_date_without_issuer_filter(self):
        fixture = collection_fixtures.TushareSourceCollectionTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        scope = copy.deepcopy(fixture.scope)
        scope["allow_dividend_market_day"] = True
        scope["requests"] = [{"api_name": "dividend", "fields": FIELDS, "max_rows": 2000,
            "params": {"imp_ann_date": "20230607"}}]
        preview = fixture.collect(scope)
        second = list(ROW)
        second[0] = "600036.SH"
        payload = {"code": 0, "data": {"fields": FIELDS.split(","), "items": [ROW, second]}}
        session = Session(Response(payload))
        with patch("quant_robot.data.sources.tushare_http._new_session", return_value=session):
            result = fixture.collect(scope, execute=True, expected_scope_sha256=preview["scope_sha256"])
        self.assertEqual(result["status"], "collected_unqualified")
        self.assertEqual(session.calls[0][1]["json"]["params"], {"imp_ann_date": "20230607"})
        self.assertEqual(json.loads((Path(result["output_dir"]) / "response_001.json").read_text()), payload)

    def test_market_day_flag_cannot_enable_multi_day_batch_other_api_or_range(self):
        fixture = collection_fixtures.TushareSourceCollectionTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        base = copy.deepcopy(fixture.scope)
        base["allow_dividend_market_day"] = True
        base["requests"] = [{"api_name": "dividend", "fields": FIELDS, "max_rows": 2000,
            "params": {"imp_ann_date": "20230607"}}]
        # First establish that this flag is understood, not just an unknown key.
        self.assertEqual(fixture.collect(base)["status"], "preview")
        invalid = []
        for flag in (1, "true", None):
            scope = copy.deepcopy(base)
            scope["allow_dividend_market_day"] = flag
            invalid.append(scope)
        scope = copy.deepcopy(base)
        scope["requests"] += [dict(scope["requests"][0], params={"imp_ann_date": "20230608"})]
        invalid.append(scope)
        for update in ({"api_name": "anns_d"}, {"max_rows": 2001},
                {"params": {"start_date": "20230101", "end_date": "20231231"}},
                {"params": {"ts_code": "000001.SZ", "imp_ann_date": "20230607"}}):
            scope = copy.deepcopy(base)
            scope["requests"][0].update(update)
            invalid.append(scope)
        with patch("quant_robot.data.sources.tushare_http._new_session") as network:
            for scope in invalid:
                with self.subTest(scope=scope), self.assertRaises(ValueError):
                    fixture.collect(scope)
        network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
