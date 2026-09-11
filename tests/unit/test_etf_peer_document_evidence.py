from __future__ import annotations

import unittest
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from quant_robot.data.etf_peer_document_evidence import review_peer_document_bundle, review_peer_document_text


FUND = "华夏沪深300交易型开放式指数证券投资基金"


class PeerDocumentEvidenceTests(unittest.TestCase):
    def review(self, *, cover=None, pages=None, title=None, published="2020-01-20"):
        return review_peer_document_text(
            symbol="510330.SH", expected_fund_name=FUND,
            index_title=title or FUND + "招募说明书更新",
            published_date=published,
            cover=cover or FUND + "招募说明书（更新）2020年1月20日公告",
            evidence_pages=pages or {58: "本基金的标的指数为沪深300指数。"},
        )

    def test_explicit_assignment_is_an_observation_not_a_history(self):
        result = self.review()
        self.assertEqual(result["declared_tracking_index"], "沪深300指数")
        self.assertEqual(result["evidence_pages"], [58])
        self.assertFalse(result["mapping_eligible"])
        self.assertIsNone(result["known_from"])
        self.assertEqual(result["document_announcement_date"], "2020-01-20")

    def test_foreign_fund_under_matching_filename_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "identity"):
            self.review(cover="华夏沪港通恒生交易型开放式指数证券投资基金招募说明书")

    def test_linked_fund_cover_cannot_match_target_prefix(self):
        with self.assertRaisesRegex(ValueError, "identity"):
            self.review(cover=FUND + "联接基金招募说明书")

    def test_generic_amendment_example_cannot_create_assignment(self):
        result = self.review(
            title="华夏基金管理有限公司关于修订旗下基金合同的公告",
            cover="华夏基金管理有限公司关于修订旗下基金合同的公告",
            pages={2: FUND + "列入适用名单。以其他基金为例，本基金的标的指数为中证港股通50指数。"},
        )
        self.assertEqual(result["status"], "manual_amendment_review")
        self.assertIsNone(result["declared_tracking_index"])

    def test_disguised_amendment_title_does_not_bypass_cover_check(self):
        with self.assertRaisesRegex(ValueError, "identity"):
            self.review(cover="某管理人关于" + FUND + "修改合同的公告")

    def test_benchmark_only_is_not_implicitly_a_tracking_assignment(self):
        result = self.review(
            title=FUND + "基金产品资料概要更新",
            cover=FUND + "基金产品资料概要更新",
            pages={2: "业绩比较基准沪深300指数收益率风险收益特征股票型。"},
        )
        self.assertEqual(result["status"], "benchmark_only")
        self.assertEqual(result["declared_benchmark"], "沪深300指数收益率")
        self.assertIsNone(result["declared_tracking_index"])

    def test_conflicting_indexes_and_return_variants_are_not_merged(self):
        with self.assertRaisesRegex(ValueError, "conflicting"):
            self.review(pages={1: "本基金的标的指数为沪深300指数。", 2: "本基金的标的指数为沪深300全收益指数。"})

    def test_cover_announcement_date_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "announcement date"):
            self.review(published="2020-01-19")

    def test_formation_date_does_not_become_publication_date(self):
        result = self.review(cover=FUND + "招募说明书基金成立日期2012年12月25日")
        self.assertIsNone(result["document_announcement_date"])
        self.assertIsNone(result["known_from"])

    def test_future_and_noncanonical_dates_are_rejected(self):
        for day in ["2026-01-01", "20200120", "2020-1-20"]:
            with self.subTest(day=day), self.assertRaises(ValueError):
                self.review(published=day)

    def test_index_mentions_without_complete_declaration_are_not_accepted(self):
        for body in ["示例中谈到沪深300指数。", "本基金的标的指数为沪深300指数", "本基金的标的指数为" + "甲" * 130 + "。"]:
            with self.subTest(body=body):
                result = self.review(pages={3: body})
                self.assertEqual(result["status"], "manual_field_review")

    def test_duplicate_same_declaration_retains_all_evidence_pages(self):
        result = self.review(pages={2: "本基金的标的指数为沪深 300 指数。", 7: "本基金的标的指数为沪深300指数。"})
        self.assertEqual(result["evidence_pages"], [2, 7])

    def test_verified_publisher_header_and_repeated_page_header(self):
        result = review_peer_document_text(
            symbol="510330.SH", expected_fund_name=FUND, expected_manager_name="华夏基金管理有限公司",
            index_title=FUND + "更新的招募说明书", published_date="2020-01-20",
            cover=FUND + "1华夏基金管理有限公司" + FUND + "更新的招募说明书",
            evidence_pages={3: "本基金的标的指数为沪深300指数。"},
        )
        self.assertEqual(result["status"], "tracking_index_observed")

    def test_product_page_header_and_delivery_date_are_distinguished(self):
        result = self.review(
            title=FUND + "_基金产品资料概要", cover="1/5" + FUND + "基金产品资料概要编制日期2020年1月19日送出日期：2020年1月20日",
        )
        self.assertEqual(result["document_announcement_date"], "2020-01-20")

    def test_delivery_date_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "announcement date"):
            self.review(cover=FUND + "基金产品资料概要送出日期：2020年1月21日")

    def test_hypothetical_quoted_or_old_terms_are_not_current_assignments(self):
        for body in ["假设本基金的标的指数为中证500指数。",
                     "以其他基金为例：本基金的标的指数为中证港股通50指数。",
                     "修订前：本基金的标的指数为中证500指数。",
                     "如果本基金的标的指数为中证500指数，则另行决定。"]:
            with self.subTest(body=body):
                result = self.review(pages={2: body})
                self.assertEqual(result["status"], "manual_scope_review")
                self.assertIsNone(result["declared_tracking_index"])


class PeerDocumentBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.pdf = root / "source.pdf"
        self.pdf.write_bytes(b"%PDF offline transport boundary fixture")
        self.packet = root / "packet.json"
        row = {"symbol": "510330.SH", "title": FUND + "招募说明书", "published_date": "2020-01-20",
               "path": str(self.pdf), "sha256": hashlib.sha256(self.pdf.read_bytes()).hexdigest(),
               "url": "https://example.invalid/source.pdf", "explicit_tracking_statements": [{"physical_page": 2}]}
        self.packet.write_text(json.dumps({"records": [row]}), encoding="utf-8")
        self.config = {"field_candidates_path": str(self.packet),
                       "field_candidates_sha256": hashlib.sha256(self.packet.read_bytes()).hexdigest(),
                       "fund_identities": {"510330.SH": FUND}}

    def test_bundle_rechecks_pdf_pages_and_stays_outside_mapping_authority(self):
        with patch("quant_robot.data.etf_peer_document_evidence._pdf_pages", return_value=(
                FUND + "招募说明书", {2: "本基金的标的指数为沪深300指数。"})) as reader:
            result = review_peer_document_bundle(self.config)
        reader.assert_called_once_with(self.pdf.read_bytes(), [2])
        self.assertEqual(result["counts"], {"tracking_index_observed": 1})
        self.assertFalse(result["historical_mapping_written"])
        self.assertFalse(result["metadata_readiness_cleared"])

    def test_changed_source_packet_or_pdf_is_rejected(self):
        self.config["field_candidates_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "packet fingerprint"):
            review_peer_document_bundle(self.config)
        self.config["field_candidates_sha256"] = hashlib.sha256(self.packet.read_bytes()).hexdigest()
        self.pdf.write_bytes(b"%PDF replaced source")
        with self.assertRaisesRegex(ValueError, "PDF source fingerprint"):
            review_peer_document_bundle(self.config)

    def test_nonphysical_page_number_is_rejected_before_pdf_read(self):
        payload = json.loads(self.packet.read_text(encoding="utf-8"))
        payload["records"][0]["explicit_tracking_statements"] = [{"physical_page": 0}]
        self.packet.write_text(json.dumps(payload), encoding="utf-8")
        self.config["field_candidates_sha256"] = hashlib.sha256(self.packet.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "page scope"):
            review_peer_document_bundle(self.config)

    def test_input_change_during_pdf_extraction_invalidates_report(self):
        def change_source(raw, pages):
            self.packet.write_text("{}", encoding="utf-8")
            return FUND + "招募说明书", {2: "本基金的标的指数为沪深300指数。"}
        with patch("quant_robot.data.etf_peer_document_evidence._pdf_pages", side_effect=change_source):
            with self.assertRaisesRegex(ValueError, "changed during"):
                review_peer_document_bundle(self.config)

    def test_sealed_date_is_rejected_before_any_pdf_read(self):
        payload = json.loads(self.packet.read_text(encoding="utf-8"))
        payload["records"][0]["published_date"] = "2026-01-02"
        self.packet.write_text(json.dumps(payload), encoding="utf-8")
        self.config["field_candidates_sha256"] = hashlib.sha256(self.packet.read_bytes()).hexdigest()
        self.pdf.unlink()
        with self.assertRaisesRegex(ValueError, "holdout"):
            review_peer_document_bundle(self.config)


if __name__ == "__main__":
    unittest.main()
