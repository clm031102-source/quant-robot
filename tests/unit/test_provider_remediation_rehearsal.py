import unittest

from quant_robot.ops.provider_remediation_rehearsal import build_provider_remediation_rehearsal


class ProviderRemediationRehearsalTests(unittest.TestCase):
    def test_rehearsal_builds_sample_reviews_and_before_after_counts(self):
        evidence = {
            "stage": "phase_3_2_provider_readiness_evidence",
            "providers": [
                {
                    "provider": "tushare",
                    "ready": False,
                    "package": "tushare",
                    "credential": "TUSHARE_TOKEN",
                    "missing": ["tushare package is not installed", "TUSHARE_TOKEN is not set"],
                },
                {
                    "provider": "ccxt",
                    "ready": False,
                    "package": "ccxt",
                    "missing": ["ccxt package is not installed"],
                },
                {
                    "provider": "yfinance",
                    "ready": False,
                    "package": "yfinance",
                    "missing": ["yfinance package is not installed"],
                },
            ],
            "parquet": {"ready": False, "missing": ["pyarrow or fastparquet package is not installed"]},
        }

        rehearsal = build_provider_remediation_rehearsal(evidence)

        self.assertEqual(rehearsal["stage"], "phase_4_11_provider_remediation_review_rehearsal")
        self.assertEqual(rehearsal["summary"]["source_remediation_items"], 5)
        self.assertEqual(rehearsal["summary"]["sample_review_rows"], 2)
        self.assertEqual(rehearsal["summary"]["source_blocking_remediation_items"], 5)
        self.assertEqual(rehearsal["summary"]["rehearsed_blocking_remediation_items"], 3)
        self.assertEqual(rehearsal["summary"]["blocker_delta"], 2)
        self.assertTrue(rehearsal["summary"]["blocks_api_boundary_after_rehearsal"])
        self.assertEqual(rehearsal["sample_review_rows"][0]["review_status"], "accepted_out_of_scope")
        self.assertEqual(rehearsal["sample_review_rows"][0]["reviewed_by"], "rehearsal")
        self.assertIn("Rehearsal only", rehearsal["sample_review_rows"][0]["evidence_note"])
        self.assertEqual(rehearsal["rehearsed_remediation_summary"]["accepted_out_of_scope"], 2)
        self.assertEqual(rehearsal["rehearsed_remediation_summary"]["needs_review"], 3)
        self.assertEqual(rehearsal["readiness_projection"]["status"], "block")
        self.assertIn("No broker", rehearsal["safety"])
        self.assertIn("Before", rehearsal["markdown"])

    def test_rehearsal_uses_current_reviewed_matrix_as_baseline(self):
        evidence = {
            "stage": "phase_3_2_provider_readiness_evidence",
            "providers": [
                {"provider": "tushare", "ready": False, "package": "tushare", "credential": "TUSHARE_TOKEN", "missing": ["TUSHARE_TOKEN is not set"]},
                {"provider": "ccxt", "ready": False, "package": "ccxt", "missing": ["ccxt package is not installed"]},
            ],
            "parquet": {"ready": True, "missing": []},
        }
        current_matrix = {
            "stage": "phase_4_7_provider_remediation_matrix",
            "summary": {
                "remediation_items": 2,
                "blocking_remediation_items": 1,
                "blocks_api_boundary": True,
                "needs_review": 0,
            },
            "remediation_items": [
                {
                    "remediation_id": "PR-tushare-credential",
                    "provider": "tushare",
                    "review_status": "blocked_external_change",
                    "blocks_provider_readiness": True,
                },
                {
                    "remediation_id": "PR-ccxt-dependency",
                    "provider": "ccxt",
                    "review_status": "accepted_out_of_scope",
                    "blocks_provider_readiness": False,
                },
            ],
        }

        rehearsal = build_provider_remediation_rehearsal(evidence, baseline_matrix=current_matrix)

        self.assertEqual(rehearsal["summary"]["source_remediation_items"], 2)
        self.assertEqual(rehearsal["summary"]["source_blocking_remediation_items"], 1)
        self.assertEqual(rehearsal["summary"]["sample_review_rows"], 0)
        self.assertEqual(rehearsal["summary"]["rehearsed_blocking_remediation_items"], 1)
        self.assertEqual(rehearsal["readiness_projection"]["status"], "block")


if __name__ == "__main__":
    unittest.main()
