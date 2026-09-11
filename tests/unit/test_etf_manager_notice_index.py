from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from quant_robot.data.etf_manager_notice_index import parse_chinaamc_notice_page, review_chinaamc_notice_bundle


def page_html(page=1, last=1, day="2020-01-20", article="123", title="基金合同修订公告"):
    return (f'<html><form id="queryForm"><input name="fundcode" value="510330">'
            f'<input name="beginDate" value="2019-01-01"><input name="endDate" value="2024-06-28">'
            '<input name="title" value=" "></form><div class="li middle-box"><div class="item">'
            f'<a href="../c/{day}/{article}.shtml">{title}</a></div><div class="item">{day}</div></div>'
            '<div class="page-mod">' + ''.join(
                f'<a class="{"cur" if p == page else ""}" onclick="thisPage({p})">{p}</a>'
                for p in range(1, last + 1)) + '</div></html>').encode("utf-8")


class ManagerNoticePageTests(unittest.TestCase):
    def parse(self, raw=None, **overrides):
        args = dict(symbol="510330.SH", start_date="2019-01-01", end_date="2024-06-28",
                    requested_page=1, title_filter="")
        args.update(overrides)
        return parse_chinaamc_notice_page(page_html() if raw is None else raw, **args)

    def test_utf8_title_and_requested_page_are_retained_without_history_claim(self):
        result = self.parse()
        self.assertEqual(result["records"][0]["title"], "基金合同修订公告")
        self.assertEqual(result["records"][0]["date"], "2020-01-20")
        self.assertEqual(result["visible_pages"], [1])
        self.assertFalse(result["historical_coverage_verified"])

    def test_query_reset_first_page_cannot_pass_as_page_two(self):
        with self.assertRaisesRegex(ValueError, "requested page"):
            self.parse(page_html(1, 5), requested_page=2)

    def test_wrong_fund_window_or_title_filter_is_rejected(self):
        for old, new in [(b'510330', b'510300'), (b'2019-01-01', b'2020-01-01'),
                         (b'name="title" value=" "', b'name="title" value="x"')]:
            with self.subTest(new=new), self.assertRaisesRegex(ValueError, "query scope"):
                self.parse(page_html().replace(old, new))

    def test_misencoded_or_empty_response_cannot_look_complete(self):
        for raw in [b'\xff', b'<html>unavailable</html>']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.parse(raw)

    def test_out_of_window_and_sealed_publication_rows_are_rejected(self):
        for day in ["2018-12-31", "2026-01-01"]:
            with self.subTest(day=day), self.assertRaisesRegex(ValueError, "publication"):
                self.parse(page_html(day=day))

    def test_article_date_mismatch_or_foreign_destination_is_rejected(self):
        for raw in [page_html().replace(b'../c/2020-01-20/', b'../c/2020-01-21/'),
                    page_html().replace(b'../c/', b'https://example.invalid/c/')]:
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "article"):
                self.parse(raw)

    def test_duplicate_query_fields_or_empty_title_are_rejected(self):
        for raw in [page_html().replace(b'</form>', b'<input name="fundcode" value="510330"></form>'),
                    page_html(title=" ")]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.parse(raw)


class ManagerNoticeBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = dict(symbol="510330.SH", start_date="2019-01-01", end_date="2024-06-28",
                           title_filter="", pages=[])

    def add(self, number, last, day="2020-01-20", article="123"):
        path = self.root / f"page{number}.html"
        raw = page_html(number, last, day, article)
        path.write_bytes(raw)
        self.config["pages"].append(dict(page=number, path=str(path), sha256=hashlib.sha256(raw).hexdigest()))

    def test_complete_visible_pages_do_not_certify_complete_history(self):
        self.add(1, 2, "2020-01-21", "124")
        self.add(2, 2)
        result = review_chinaamc_notice_bundle(self.config)
        self.assertEqual(len(result["records"]), 2)
        self.assertTrue(result["visible_index_pagination_complete"])
        self.assertFalse(result["historical_coverage_verified"])
        self.assertFalse(result["mapping_authority_written"])

    def test_missing_visible_page_is_rejected(self):
        self.add(1, 2)
        with self.assertRaisesRegex(ValueError, "missing.*page"):
            review_chinaamc_notice_bundle(self.config)

    def test_repeated_article_across_pages_is_rejected(self):
        self.add(1, 2)
        self.add(2, 2)
        with self.assertRaisesRegex(ValueError, "duplicate article"):
            review_chinaamc_notice_bundle(self.config)

    def test_changed_source_page_is_rejected(self):
        self.add(1, 1)
        Path(self.config["pages"][0]["path"]).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            review_chinaamc_notice_bundle(self.config)

    def test_invalid_scope_is_rejected_before_source_read(self):
        self.add(1, 1)
        Path(self.config["pages"][0]["path"]).unlink()
        self.config["end_date"] = "2026-01-01"
        with self.assertRaisesRegex(ValueError, "holdout"):
            review_chinaamc_notice_bundle(self.config)

    def test_source_order_cannot_mask_nonchronological_pagination(self):
        self.add(1, 2, "2020-01-20", "123")
        self.add(2, 2, "2020-01-21", "124")
        with self.assertRaisesRegex(ValueError, "chronological"):
            review_chinaamc_notice_bundle(self.config)

    def test_alternate_or_unhandled_numeric_page_link_cannot_disappear(self):
        self.add(1, 2)
        path = Path(self.config["pages"][0]["path"])
        original = path.read_bytes()
        for handler in [b'thisPage(2);', b'thisPage( 2 )', b'goSomewhere(2)', b'']:
            with self.subTest(handler=handler):
                raw = original.replace(b'thisPage(2)', handler)
                path.write_bytes(raw)
                self.config["pages"][0]["sha256"] = hashlib.sha256(raw).hexdigest()
                with self.assertRaisesRegex(ValueError, "page"):
                    review_chinaamc_notice_bundle(self.config)


if __name__ == "__main__":
    unittest.main()
