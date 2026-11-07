"""Artificial JSON and calendars only; no source files, credentials or HTTP."""
from copy import deepcopy
from datetime import date, timedelta
import json
import unittest

from quant_robot.ops import tushare_fund_daily_wire as W


def request(dates=("20140102", "20140103")):
    return {"params": {"ts_code": "510300.SH"}, "expected_trade_dates": list(dates), "expected_rows": len(dates)}


def body(dates=("20140102", "20140103"), *, symbol="510300.SH", cells=None):
    cells = cells or '123456789123456789123456789,1e999999999,0.0100,-7,"2.500",null'
    rows = [json.dumps([symbol, d])[:-1]+","+cells+"]" for d in dates]
    return ('{"code":0,"msg":"","data":{"fields":'+json.dumps(list(W.FIELDS))+',"items":['+",".join(rows)+"]}}").encode()


def artificial_manifest():
    cursor, end = date(2013, 12, 5), date(2024, 1, 2)
    days = []
    while cursor < end:
        if cursor.weekday() < 5:
            days.append(cursor.isoformat())
        cursor += timedelta(days=1)
    days = days[:2453]+[end.isoformat()]
    rows = []
    for year in range(2013, 2025):
        selected = [d for d in days if d[:4] == str(year)]
        for symbol in W.SYMBOLS:
            n = len(rows)+1
            identity = f"{n:02d}_fund_daily_{symbol.replace('.', '_')}_{year}"
            rows.append({"order": n, "id": identity, "role": f"fund_daily_{symbol[:6]}_{year}_provider_wire",
                         "endpoint": W.URL, "method": "POST", "api_name": W.API,
                         "params": {"ts_code": symbol, "start_date": "20131205" if year == 2013 else f"{year}0101",
                                    "end_date": "20240102" if year == 2024 else f"{year}1231"},
                         "fields": ",".join(W.FIELDS), "expected_trade_dates": [d.replace("-", "") for d in selected],
                         "expected_rows": len(selected), "expected_ISO_dates_sha256": W.date_digest(selected),
                         "expected_symbol_date_sha256": W.date_digest(selected, symbol),
                         "planned_capture_directory": f"capture/requests/{identity}", "actual_response_ref": None})
    manifest = {"artifact_type": "constant_mix_fixed_24_provider_requests_v1", "symbols": list(W.SYMBOLS),
                "range": [days[0], days[-1]], "request_count": 24, "expected_total_symbol_date_rows": 4908,
                "old_dayk_or_971_mapped_rows_used_as_authority": False,
                "request_budget": {"max_POST": 24, "GET": 0, "automatic_pagination": 0, "retry": 0,
                                   "redirect": 0, "substitute_dates_or_symbols": False, "resume_failed_batch": False},
                "requests": rows}
    return manifest, days


class WireStructureTests(unittest.TestCase):
    def test_ascending_descending_metadata_without_numeric_conversion(self):
        results = [W.inspect_structure(body(ds), request()) for ds in (("20140102", "20140103"), ("20140103", "20140102"))]
        self.assertEqual([r["source_row_order"] for r in results], ["ascending", "descending"])
        self.assertEqual(results[0]["expected_symbol_date_sha256"], results[1]["expected_symbol_date_sha256"])
        self.assertEqual(results[0]["financial_cell_syntax_counts"], {"JSON_numeric_token": 8, "numeric_string": 2, "null": 2})
        for result in results:
            self.assertFalse(result["numerical_quality_verified"])
            self.assertFalse(result["financial_numeric_values_decoded"])
            self.assertNotIn("123456789", json.dumps(result))
            self.assertNotIn("999999999", json.dumps(result))
            self.assertNotIn("2.500", json.dumps(result))

    def test_number_spellings_preserved_and_conversion_guarded(self):
        parsed = W.decode_opaque(body())
        row = parsed["data"]["items"][0]
        self.assertEqual(str(row[4]), "0.0100")
        self.assertEqual(str(row[3]), "1e999999999")
        with self.assertRaisesRegex(W.WireError, "financial_conversion_forbidden"):
            float(row[3])
        with self.assertRaisesRegex(W.WireError, "financial_conversion_forbidden"):
            int(row[2])

    def test_missing_extra_duplicate_date_metadata_only(self):
        for dates in (("20140102",), ("20140102", "20140103", "20140106"), ("20140102", "20140102")):
            with self.subTest(dates=dates), self.assertRaises(W.WireError) as caught:
                W.inspect_structure(body(dates), request())
            self.assertEqual(caught.exception.code, "response_date_set_mismatch")
            self.assertEqual(set(caught.exception.metadata), {"missing_dates", "unexpected_dates", "duplicate_dates"})
            self.assertNotIn("123456789", json.dumps(caught.exception.metadata))

    def test_symbol_invalid_date_field_order_and_row_shape_rejected(self):
        changed_order = body().replace(b'"open", "high"', b'"high", "open"')
        bad_width = body().replace(b',null]', b']')
        for raw, code in ((body(symbol="518880.SH"), "response_symbol_mismatch"),
                          (body(("20140231",)), "invalid_identity_date"),
                          (changed_order, "exact_field_order_required"), (bad_width, "row_width_invalid")):
            with self.subTest(code=code), self.assertRaisesRegex(W.WireError, code):
                W.inspect_structure(raw, request())

    def test_duplicate_keys_error_envelope_and_pagination_never_echo_provider_message(self):
        cases = [(b'{"code":0,"code":0}', "duplicate_JSON_key"),
                 (b'{"code":2014,"msg":"private error 987654321"}', "provider_envelope_rejected"),
                 (body().replace(b'"items":', b'"has_more":true,"items":'), "pagination_not_allowed"),
                 (body().replace(b'"code":0', b'"code":false'), "provider_envelope_rejected")]
        for raw, code in cases:
            with self.subTest(code=code), self.assertRaises(W.WireError) as caught:
                W.inspect_structure(raw, request())
            self.assertEqual(str(caught.exception), code)
            self.assertNotIn("987654321", str(caught.exception))

    def test_financial_types_and_nonstandard_numbers_rejected(self):
        for value in ('true', '{}', '[]', '"NaN"', '"not-a-number"'):
            with self.subTest(value=value), self.assertRaisesRegex(W.WireError, "financial_cell_schema_invalid"):
                W.inspect_structure(body(cells=value+',1,1,1,1,1'), request())
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value), self.assertRaisesRegex(W.WireError, "nonstandard_JSON_number"):
                W.inspect_structure(body(cells=value+',1,1,1,1,1'), request())

    def test_encoded_credential_echo_and_secret_keys_never_retained(self):
        secret = "credential_fixturE"
        raw = body().replace(b'"msg":""', ('"msg":"'+secret+'"').encode())
        escaped = raw.replace(secret.encode(), b'credential_fixtur\\u0045')
        for payload in (raw, escaped):
            with self.assertRaisesRegex(W.WireError, "credential_echo_not_retained"):
                W.inspect_structure(payload, request(), token=secret)
        with self.assertRaisesRegex(W.WireError, "credential_field_not_retained"):
            W.decode_opaque(b'{"data":{"token":"different-secret"}}')

    def test_depth_size_and_row_limits(self):
        with self.assertRaisesRegex(W.WireError, "response_byte_limit"):
            W.decode_opaque(b' '*(W.MAX_BYTES+1))
        with self.assertRaisesRegex(W.WireError, "JSON_depth_limit"):
            W.decode_opaque(('['*10+'0'+']'*10).encode())
        with self.assertRaisesRegex(W.WireError, "response_rows_limit"):
            W.inspect_structure(body(("20140102",)*367), request())

    def test_long_numeric_lexeme_remains_opaque_and_is_not_printed(self):
        raw = body(cells=('8'*6000)+',1,1,1,1,1')
        result = W.inspect_structure(raw, request())
        self.assertEqual(result["rows"], 2)
        self.assertNotIn("888888", json.dumps(result))


class FixedManifestTests(unittest.TestCase):
    def test_complete_fixture_calendar_and_exact_twenty_four_roles(self):
        manifest, days = artificial_manifest()
        self.assertEqual(W.validate_manifest(manifest, days)["expected_rows"], 4908)

    def test_redirect_symbol_period_dates_order_budget_or_role_changes_fail(self):
        original, days = artificial_manifest()
        changes = [lambda m: m["requests"][0].update(endpoint="https://other.example"),
                   lambda m: m["requests"][0]["params"].update(ts_code="511220.SH"),
                   lambda m: m["requests"][0]["params"].update(start_date="20130101"),
                   lambda m: m["requests"][0].update(expected_trade_dates=[]),
                   lambda m: m["requests"].reverse(),
                   lambda m: m["request_budget"].update(retry=1),
                   lambda m: m["requests"][0].update(planned_capture_directory="../../other"),
                   lambda m: m.update(old_dayk_or_971_mapped_rows_used_as_authority=True)]
        for change in changes:
            modified = deepcopy(original); change(modified)
            with self.subTest(change=changes.index(change)), self.assertRaises(W.WireError):
                W.validate_manifest(modified, days)


if __name__ == "__main__":
    unittest.main()
