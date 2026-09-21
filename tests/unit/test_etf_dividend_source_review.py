import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.data.etf_dividend_source_review import review_dividend_sources
from tests.unit.test_etf_dividend_notice import NOTICE, announcement_page


class DividendSourceReviewTests(unittest.TestCase):
    def test_source_to_ledger_preserves_record_ex_and_pay_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = fixture(Path(tmp))
            with patch("quant_robot.data.etf_dividend_source_review._pdf_text", return_value=([NOTICE], "synthetic text")):
                result = review_dividend_sources(config, output_dir=Path(tmp) / "out")
            drill = result["fixture_drill"]
            self.assertEqual(drill["cash_received"], 7.2)
            self.assertEqual(drill["steps"], [
                {"date": "2021-01-15", "cash_before_close": 0.0, "receivable_before_close": 0.0, "cash_after_close": 0.0},
                {"date": "2021-01-18", "cash_before_close": 0.0, "receivable_before_close": 7.2, "cash_after_close": 0.0},
                {"date": "2021-01-21", "cash_before_close": 0.0, "receivable_before_close": 7.2, "cash_after_close": 7.2}])
            self.assertFalse(result["execution_accounting_source_verified"])
            self.assertFalse(drill["source_audit_verified"])
            self.assertEqual(drill["counts_as_forward_paper_days"], 0)

    def test_filtered_index_is_not_complete_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = fixture(root, keyword="分红")
            with self.assertRaisesRegex(ValueError, "unfiltered"):
                review_dividend_sources(config, output_dir=root / "out")

    def test_unreviewed_notice_and_changed_pdf_are_blocked(self):
        for change in ("missing", "mutated"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); config = fixture(root)
                if change == "missing": config["notices"] = []
                else: Path(config["notices"][0]["pdf"]).write_bytes(b"altered")
                with self.assertRaisesRegex(ValueError, "match all|fingerprint"):
                    review_dividend_sources(config, output_dir=root / "out")

    def test_mixed_or_gapped_requested_scope_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); config = fixture(root)
            config["window_start"] = "2020-01-01"
            with self.assertRaisesRegex(ValueError, "cover the requested"):
                review_dividend_sources(config, output_dir=root / "out")

    def test_missing_tax_statement_still_reports_gross_notice_but_skips_cash_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); config = fixture(root)
            with patch("quant_robot.data.etf_dividend_source_review._pdf_text", return_value=(
                    [NOTICE.replace("暂不征收个人所得税和企业所得税", "")], "synthetic text")):
                result = review_dividend_sources(config, output_dir=root / "out")
            self.assertFalse(result["fixture_drill"]["ran"])
            self.assertFalse((root / "out/notice_ledger_fixture.json").exists())

    def test_duplicate_economic_events_fail_even_when_tax_fixture_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); config = fixture(root)
            response = root / "response.json"
            page = announcement_page()
            other = dict(page["result"][0])
            other["URL"] = other["URL"].replace("_1.pdf", "_2.pdf")
            page["result"].append(other); page["pageHelp"]["total"] = 2
            response.write_text(json.dumps(page), encoding="utf-8")
            request = root / "request.json"
            record = json.loads(request.read_text(encoding="utf-8"))
            record["response_sha256"] = digest(response)
            request.write_text(json.dumps(record), encoding="utf-8")
            config["index_pages"][0]["request_record_sha256"] = digest(request)
            config["notices"].append({**config["notices"][0], "url_path": other["URL"]})
            first = NOTICE.replace("暂不征收个人所得税和企业所得税", "")
            with patch("quant_robot.data.etf_dividend_source_review._pdf_text", side_effect=[
                    ([first], "synthetic"), ([first.replace("0.7200", "0.8000")], "synthetic")]):
                with self.assertRaisesRegex(ValueError, "duplicate|conflicting"):
                    review_dividend_sources(config, output_dir=root / "out")


def fixture(root, *, keyword=""):
    response = root / "response.json"
    response.write_text(json.dumps(announcement_page()), encoding="utf-8")
    request = root / "request.json"
    request.write_text(json.dumps({"params": {"TITLE": keyword, "BULLETIN_TYPE": "",
        "SECURITY_CODE": "510300", "sqlId": "COMMON_PL_JJXX_JJGG_NEW_L",
        "START_DATE": "2021-01-01", "END_DATE": "2021-12-31"},
        "response_sha256": digest(response)}), encoding="utf-8")
    pdf = root / "notice.pdf"
    pdf.write_bytes(b"%PDF fixture is decoded by the test double")
    return {"symbol": "510300.SH", "window_start": "2021-01-01", "window_end": "2021-12-31",
        "index_pages": [{"request_record": str(request), "request_record_sha256": digest(request), "response": str(response)}],
        "notices": [{"url_path": announcement_page()["result"][0]["URL"], "pdf": str(pdf), "sha256": digest(pdf)}]}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
