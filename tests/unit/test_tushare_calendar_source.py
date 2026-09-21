import copy
import unittest
from unittest.mock import patch

from quant_robot.data.sources.tushare_http import TushareSourceError, TushareSourceHttpClient
from tests.unit.test_tushare_source_http import Response, Session


FIELDS = "exchange,cal_date,is_open,pretrade_date"
PARAMS = {"exchange": "SSE", "start_date": "20240105", "end_date": "20240107"}
ROWS = [["SSE", "20240105", 1, "20240104"],
        ["SSE", "20240106", "0", "20240105"],
        ["SSE", "20240107", "0", "20240105"]]


def payload(rows):
    return {"code": 0, "data": {"fields": FIELDS.split(","), "items": rows}}


class TushareCalendarSourceTests(unittest.TestCase):
    def client(self):
        return TushareSourceHttpClient(token="private-test-token", max_requests=1,
                                      max_date="20251231", trust_env=False)

    def query(self, rows, *, params=None, max_rows=3):
        client = self.client()
        session = Session(Response(payload(rows)))
        with patch("quant_robot.data.sources.tushare_http._new_session", return_value=session):
            frame = client.query("trade_cal", fields=FIELDS, max_rows=max_rows, **(params or PARAMS))
        return frame, client, session

    def test_complete_calendar_keeps_closed_days_and_original_row_order(self):
        rows = list(reversed(copy.deepcopy(ROWS)))
        frame, client, session = self.query(rows)
        self.assertEqual(frame.values.tolist(), rows)
        self.assertEqual(client.last_payload["data"]["items"], rows)
        self.assertEqual(client.last_attempt["status"], "received")
        self.assertEqual(session.calls[0][1]["json"]["params"], PARAMS)
        self.assertFalse(session.trust_env)
        self.assertTrue(session.calls[0][1]["verify"])

    def test_leap_day_is_required_in_closed_interval(self):
        params = {"exchange": "SZSE", "start_date": "20240228", "end_date": "20240301"}
        rows = [["SZSE", "20240228", "1", "20240227"],
                ["SZSE", "20240229", "1", "20240228"],
                ["SZSE", "20240301", "1", "20240229"]]
        self.assertEqual(len(self.query(rows, params=params)[0]), 3)
        with self.assertRaises(TushareSourceError):
            self.query([rows[0], rows[2]], params=params)

    def test_scope_requires_one_cash_exchange_all_days_and_exact_fields(self):
        invalid = []
        for update in ({"exchange": ""}, {"exchange": "DCE"}, {"exchange": "SSE,SZSE"},
                       {"is_open": "1"}, {"ts_code": "510300.SH"},
                       {"end_date": "20260101"}, {"start_date": "20240108"},
                       {"start_date": "20230229"}):
            invalid.append((FIELDS, 3, {**PARAMS, **update}))
        invalid += [(FIELDS, 2, PARAMS), (FIELDS, 3, {"exchange": "SSE"}),
                    ("exchange,cal_date,is_open", 3, PARAMS),
                    (FIELDS + ",close", 3, PARAMS),
                    (FIELDS, 400, {"exchange": "SSE", "start_date": "20230101", "end_date": "20240102"})]
        with patch("quant_robot.data.sources.tushare_http._new_session") as network:
            for fields, budget, params in invalid:
                client = self.client()
                with self.subTest(fields=fields, params=params), self.assertRaises(TushareSourceError):
                    client.query("trade_cal", fields=fields, max_rows=budget, **params)
                self.assertEqual(client.requests_used, 0)
        network.assert_not_called()

    def test_empty_or_missing_civil_dates_do_not_certify_no_trading(self):
        for rows in ([], ROWS[:1], [ROWS[0], ROWS[2]]):
            with self.subTest(rows=rows), self.assertRaises(TushareSourceError):
                self.query(rows)

    def test_duplicate_date_or_other_exchange_is_rejected(self):
        duplicate = [ROWS[0], ROWS[1], ROWS[1]]
        other = copy.deepcopy(ROWS)
        other[1][0] = "SZSE"
        for rows in (duplicate, other):
            with self.subTest(rows=rows), self.assertRaises(TushareSourceError):
                self.query(rows)

    def test_open_status_requires_literal_binary_value(self):
        for value in (True, False, 1.0, "01", "closed", None, 2):
            rows = copy.deepcopy(ROWS)
            rows[1][2] = value
            with self.subTest(value=value), self.assertRaises(TushareSourceError):
                self.query(rows)

    def test_pretrade_date_chain_rejects_same_day_missing_and_closed_predecessor(self):
        for index, value in ((0, "20240105"), (0, None), (1, "20240104"),
                             (2, "20240106"), (2, "20240230")):
            rows = copy.deepcopy(ROWS)
            rows[index][3] = value
            with self.subTest(index=index, value=value), self.assertRaises(TushareSourceError):
                self.query(rows)

    def test_response_cannot_leave_frozen_date_range(self):
        rows = copy.deepcopy(ROWS)
        rows[-1][1] = "20240108"
        with self.assertRaises(TushareSourceError):
            self.query(rows)

    def test_one_closed_day_is_valid_with_prior_trade_outside_range(self):
        params = {"exchange": "SSE", "start_date": "20240106", "end_date": "20240106"}
        frame, _, _ = self.query([ROWS[1]], params=params, max_rows=1)
        self.assertEqual(frame.iloc[0]["pretrade_date"], "20240105")


if __name__ == "__main__":
    unittest.main()
