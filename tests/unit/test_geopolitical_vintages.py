import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
from datetime import datetime

from quant_robot.data.sources.geopolitical_vintages import (
    LABEL, LIMIT, MONTHS, NEW_MONTHS, collect, fetch_once, history_url, protocol_sha, raw_url, select_commit, sha, source_window,
)


def commit(letter, author, committer=None):
    return {"sha": letter * 40, "commit": {"author": {"date": author},
            "committer": {"date": committer or author}}}


class GeopoliticalVintagesTests(unittest.TestCase):
    def test_protocol_fingerprints_match_gate_newlines_but_originals_do_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "lf.md", Path(tmp) / "crlf.md"
            a.write_bytes(b"same\nprotocol\n")
            b.write_bytes(b"same\r\nprotocol\r\n")
            self.assertEqual(protocol_sha(a), protocol_sha(b))
            self.assertNotEqual(sha(a), sha(b))
            b.write_bytes(b"changed\r\nprotocol\r\n")
            self.assertNotEqual(protocol_sha(a), protocol_sha(b))

    def test_copying_scope_does_not_grant_another_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "another location"):
                collect(Path(tmp) / "copied/scope.json", repo_root=Path(tmp))

    def test_exact_window_excludes_later_values_and_rejects_bad_sources(self):
        rows = [["month", "GPRT", "var_name", "var_label"]]
        for n in range(2021 * 12 + 3, 2022 * 12 + 5):
            rows.append([datetime((n - 1) // 12, (n - 1) % 12 + 1, 1), float(n), "", ""])
        rows[1][2:] = ["GPRT", LABEL]
        rows[-1][1] = float("nan")  # Later observation is deliberately excluded.
        value_type = [2]
        sheet = SimpleNamespace(nrows=len(rows), row_values=lambda r: rows[r],
                                cell_value=lambda r, c: rows[r][c],
                                cell=lambda r, c: SimpleNamespace(ctype=3 if c == 0 else value_type[0], value=rows[r][c]))
        book = SimpleNamespace(sheet_by_index=lambda i: sheet, datemode=0)
        decoder = SimpleNamespace(open_workbook=lambda p: book, XL_CELL_DATE=3, XL_CELL_NUMBER=2,
                                  xldate_as_datetime=lambda value, mode: value)
        with patch.dict("sys.modules", {"xlrd": decoder}):
            window = source_window(Path("unused.xls"), "202204")
            self.assertEqual((len(window), window[0]["month"], window[-1]["month"]),
                             (13, "2021-03", "2022-03"))
            for r, c, bad in [(1, 3, "Other index"), (2, 1, -1),
                              (2, 1, float("nan")), (2, 0, rows[1][0])]:
                old = rows[r][c]
                rows[r][c] = bad
                with self.subTest(row=r, column=c), self.assertRaises(ValueError):
                    source_window(Path("unused.xls"), "202204")
                rows[r][c] = old
            for kind in (4, 5):  # Excel Boolean and error codes are numeric Python values.
                value_type[0] = kind
                with self.subTest(cell_type=kind), self.assertRaises(ValueError):
                    source_window(Path("unused.xls"), "202204")

    def test_exact_finite_months_and_immutable_urls(self):
        self.assertEqual((len(MONTHS), len(NEW_MONTHS)), (46, 44))
        self.assertEqual((NEW_MONTHS[0], NEW_MONTHS[-1]), ("202204", "202511"))
        self.assertIn("path=gpr_archive_files%2Fdata_gpr_export_202204.xls", history_url("202204"))
        with self.assertRaises(ValueError):
            history_url("202601")
        with self.assertRaises(ValueError):
            raw_url("202204", "master")

    def test_both_clocks_strictly_before_cutoff(self):
        history = [commit("a", "2022-04-01T00:00:00Z", "2022-04-14T16:00:00Z"),
                   commit("b", "2022-04-14T15:59:59Z")]
        receipt = {"status_code": 200, "content_type": "application/json", "link": None}
        result = select_commit(json.dumps(history).encode(), receipt, "202204")
        self.assertEqual(result["commit_sha"], "b" * 40)

    def test_incomplete_ambiguous_and_future_histories_are_unknown(self):
        receipt = {"status_code": 200, "content_type": "application/json", "link": None}
        good = commit("a", "2022-04-01T00:00:00Z")
        cases = [([], receipt), ([good], {**receipt, "link": '<next>; rel="next"'}),
                 ([good, good], receipt),
                 ([commit("a", "2022-04-02T00:00:00Z", "2022-04-01T00:00:00Z")], receipt),
                 ([commit("a", "2022-04-14T16:00:00Z")], receipt)]
        for history, meta in cases:
            with self.subTest(history=history, meta=meta), self.assertRaises(ValueError):
                select_commit(json.dumps(history).encode(), meta, "202204")

    def test_request_claim_prevents_retry_and_records_raw_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            response = Mock(status_code=200, headers={"Content-Type": "application/json"})
            response.iter_content.return_value = [b"[]"]
            session = Mock()
            session.get.return_value.__enter__ = Mock(return_value=response)
            session.get.return_value.__exit__ = Mock(return_value=False)
            result = fetch_once(folder, "202204_history", history_url("202204"), "f" * 64, session)
            self.assertTrue(result["body_complete"])
            self.assertEqual(result["bytes"], 2)
            self.assertEqual(session.get.call_args.kwargs["allow_redirects"], False)
            with self.assertRaises(FileExistsError):
                fetch_once(folder, "202204_history", history_url("202204"), "f" * 64, session)
            self.assertEqual(session.get.call_count, 1)

    def test_oversized_body_is_not_accepted_as_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            response = Mock(status_code=200, headers={})
            response.iter_content.return_value = [b"x" * (LIMIT + 1)]
            session = Mock()
            session.get.return_value.__enter__ = Mock(return_value=response)
            session.get.return_value.__exit__ = Mock(return_value=False)
            result = fetch_once(Path(tmp), "202204_vintage", raw_url("202204", "a" * 40), "f" * 64, session)
            self.assertFalse(result["body_complete"])
            self.assertEqual(result["status"], "failed")
            self.assertFalse((Path(tmp) / "202204_vintage.xls").exists())
            self.assertTrue((Path(tmp) / "202204_vintage_receipt.json").exists())


if __name__ == "__main__":
    unittest.main()
