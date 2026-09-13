import json
import unittest
from unittest.mock import patch

from quant_robot.data.sources.tushare_http import TushareSourceError, TushareSourceHttpClient


class Response:
    def __init__(self, payload=None, status=200, raw=None):
        self.status_code = status
        self.raw = raw if raw is not None else json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_content(self, chunk_size):
        for offset in range(0, len(self.raw), chunk_size):
            yield self.raw[offset:offset + chunk_size]


class Session:
    def __init__(self, response):
        self.response = response
        self.trust_env = True
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class TushareSourceHttpTests(unittest.TestCase):
    def client(self, **kwargs):
        return TushareSourceHttpClient(
            token="private-test-token", max_requests=1, max_date="20240119", **kwargs,
        )

    def query(self, client, **kwargs):
        params = {"ts_code": "510300.SH", "trade_date": "20240118"}
        params.update(kwargs)
        return client.query("fund_adj", fields="ts_code,trade_date,adj_factor", max_rows=3, **params)

    def payload(self, rows=None, columns=None):
        return {"code": 0, "data": {
            "fields": columns or ["ts_code", "trade_date", "adj_factor"],
            "items": rows if rows is not None else [["510300.SH", "20240118", 1.2]],
        }}

    def test_http_error_cannot_become_empty_source_success(self):
        session = Session(Response(status=503))
        client = self.client()
        with patch("quant_robot.data.sources.tushare_http._new_session", return_value=session):
            with self.assertRaises(TushareSourceError) as error:
                self.query(client)
        self.assertEqual(error.exception.kind, "http_error")
        self.assertEqual(client.last_attempt["http_status"], 503)
        self.assertEqual(client.last_attempt["status"], "failed")
        self.assertEqual(len(session.calls), 1)

    def test_provider_rejection_is_distinct_redacted_and_budget_cannot_retry(self):
        session = Session(Response({"code": 40203, "msg": "denied private-test-token"}))
        client = self.client()
        with patch("quant_robot.data.sources.tushare_http._new_session", return_value=session):
            with self.assertRaises(TushareSourceError) as error:
                self.query(client)
            self.assertEqual(error.exception.kind, "provider_rejected")
            self.assertNotIn("private-test-token", str(error.exception))
            with self.assertRaisesRegex(TushareSourceError, "budget"):
                self.query(client)
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(client.last_attempt["api_code"], 40203)

    def test_direct_transport_is_explicit_tls_uses_fixed_host_and_raw_values_survive(self):
        session = Session(Response(self.payload()))
        client = self.client(trust_env=False)
        with patch("quant_robot.data.sources.tushare_http._new_session", return_value=session):
            frame = self.query(client)
        self.assertFalse(session.trust_env)
        self.assertEqual(frame.loc[0, "adj_factor"], 1.2)
        self.assertEqual(client.last_attempt["status"], "received")
        self.assertEqual(session.calls[0][0], "https://api.tushare.pro")
        self.assertFalse(session.calls[0][1]["allow_redirects"])
        self.assertTrue(session.calls[0][1]["verify"])
        self.assertEqual(session.calls[0][1]["json"]["params"]["trade_date"], "20240118")

    def test_explicit_empty_response_retains_schema_and_is_not_no_event_certification(self):
        session = Session(Response(self.payload(rows=[])))
        client = self.client()
        with patch("quant_robot.data.sources.tushare_http._new_session", return_value=session):
            frame = self.query(client)
        self.assertTrue(frame.empty)
        self.assertEqual(list(frame), ["ts_code", "trade_date", "adj_factor"])
        self.assertEqual(client.last_attempt["status"], "empty_unqualified")

    def test_invalid_request_never_reaches_network_or_consumes_budget(self):
        client = self.client()
        with patch("quant_robot.data.sources.tushare_http._new_session") as network:
            for kwargs in ({"trade_date": "20260101"}, {"trade_date": ""}):
                with self.subTest(kwargs=kwargs), self.assertRaises(TushareSourceError):
                    self.query(client, **kwargs)
            with self.assertRaises(TushareSourceError):
                client.query("unknown_api", fields="ts_code,trade_date", max_rows=3, trade_date="20240118")
        network.assert_not_called()
        self.assertEqual(client.requests_used, 0)

    def test_rejects_wrong_columns_dates_symbols_and_excess_rows(self):
        payloads = [
            self.payload(columns=["ts_code", "trade_date", "wrong"]),
            self.payload(rows=[["510300.SH", "20240119", 1.2]]),
            self.payload(rows=[["510500.SH", "20240118", 1.2]]),
            self.payload(rows=[["510300.SH", "20240118", 1.2]] * 4),
            {"code": 0, "data": {"fields": ["ts_code", "trade_date", "trade_date"], "items": []}},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                session = Session(Response(payload))
                with patch("quant_robot.data.sources.tushare_http._new_session", return_value=session):
                    with self.assertRaises(TushareSourceError):
                        self.query(self.client())

    def test_network_errors_and_oversized_or_invalid_json_are_failed_attempts(self):
        for response in (TimeoutError("private-test-token timed out"), Response(raw=b"x" * 51), Response(raw=b"{broken")):
            client = self.client(max_response_bytes=50)
            with patch("quant_robot.data.sources.tushare_http._new_session", return_value=Session(response)):
                with self.assertRaises(TushareSourceError) as error:
                    self.query(client)
            self.assertEqual(client.requests_used, 1)
            self.assertEqual(client.last_attempt["status"], "failed")
            self.assertNotIn("private-test-token", str(error.exception))

    def test_closed_ranges_reject_future_or_inverted_requests_without_network(self):
        client = self.client()
        with patch("quant_robot.data.sources.tushare_http._new_session") as network:
            for bounds in (("20240119", "20240118"), ("20240117", "20240120")):
                with self.subTest(bounds=bounds), self.assertRaises(TushareSourceError):
                    client.query("fund_adj", fields="ts_code,trade_date,adj_factor", max_rows=3,
                        ts_code="510300.SH", start_date=bounds[0], end_date=bounds[1])
        network.assert_not_called()

    def test_rejects_nonfinite_or_nested_source_values(self):
        for value in (float("nan"), float("inf"), {"echo": "private-test-token"}):
            session = Session(Response(self.payload(rows=[["510300.SH", "20240118", value]])))
            with patch("quant_robot.data.sources.tushare_http._new_session", return_value=session):
                with self.assertRaises(TushareSourceError):
                    self.query(self.client())

    def test_preserves_raw_duplicate_disclosures_and_redacts_echoed_strings(self):
        payload = {"code": 0, "data": {"fields": ["ts_code", "ann_date", "title"],
            "items": [["510300.SH", "20240118", "private-test-token"]] * 2}}
        session = Session(Response(payload))
        client = self.client()
        with patch("quant_robot.data.sources.tushare_http._new_session", return_value=session):
            result = client.query("anns_d", fields="ts_code,ann_date,title", max_rows=2, ann_date="20240118")
        self.assertEqual(len(result), 2)
        self.assertEqual(result.title.tolist(), ["[REDACTED]", "[REDACTED]"])


if __name__ == "__main__":
    unittest.main()
