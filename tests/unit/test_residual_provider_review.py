import unittest

from quant_robot.ops.residual_provider_review import build_residual_provider_review_pack


class ResidualProviderReviewTests(unittest.TestCase):
    def test_pack_extracts_residual_blocking_provider_items(self):
        rehearsal = {
            "stage": "phase_4_11_provider_remediation_review_rehearsal",
            "summary": {
                "source_remediation_items": 3,
                "sample_review_rows": 1,
                "source_blocking_remediation_items": 3,
                "rehearsed_blocking_remediation_items": 2,
                "blocker_delta": 1,
                "blocks_api_boundary_after_rehearsal": True,
            },
            "rehearsed_remediation_items": [
                {
                    "remediation_id": "PR-accepted",
                    "provider": "akshare",
                    "blocker_type": "dependency",
                    "blocker": "akshare package is not installed",
                    "review_status": "accepted_out_of_scope",
                    "evidence_note": "accepted",
                    "verification_command": "python scripts\\check_readiness.py",
                    "resolution_hint": "scope decision",
                    "blocks_provider_readiness": False,
                    "local_only": True,
                },
                {
                    "remediation_id": "PR-open-1",
                    "provider": "tushare",
                    "blocker_type": "dependency",
                    "blocker": "tushare package is not installed",
                    "review_status": "needs_review",
                    "evidence_note": "",
                    "verification_command": "python scripts\\check_readiness.py",
                    "resolution_hint": "install locally",
                    "blocks_provider_readiness": True,
                    "local_only": True,
                },
                {
                    "remediation_id": "PR-open-2",
                    "provider": "parquet",
                    "blocker_type": "storage_dependency",
                    "blocker": "pyarrow or fastparquet package is not installed",
                    "review_status": "blocked_external_change",
                    "evidence_note": "waiting on env",
                    "verification_command": "python scripts\\check_readiness.py",
                    "resolution_hint": "install storage engine locally",
                    "blocks_provider_readiness": True,
                    "local_only": True,
                },
            ],
        }

        pack = build_residual_provider_review_pack(rehearsal)

        self.assertEqual(pack["stage"], "phase_4_15_residual_provider_review_pack")
        self.assertEqual(pack["summary"]["residual_remediation_items"], 2)
        self.assertEqual(pack["summary"]["sample_cleared_remediation_items"], 1)
        self.assertTrue(pack["summary"]["blocks_api_boundary_after_review"])
        self.assertEqual([row["remediation_id"] for row in pack["residual_items"]], ["PR-open-1", "PR-open-2"])
        self.assertEqual(len(pack["review_template_rows"]), 2)
        self.assertEqual(pack["review_template_rows"][0]["review_status"], "needs_review")
        self.assertIn("--review-file", pack["action_queue"][2]["command"])
        self.assertIn("No broker", pack["safety"])
        self.assertIn("Residual Provider Review Pack", pack["markdown"])

    def test_pack_prefers_current_remediation_matrix_when_supplied(self):
        rehearsal = {
            "stage": "phase_4_11_provider_remediation_review_rehearsal",
            "summary": {
                "source_remediation_items": 1,
                "sample_review_rows": 0,
                "source_blocking_remediation_items": 1,
                "rehearsed_blocking_remediation_items": 1,
            },
            "rehearsed_remediation_items": [
                {
                    "remediation_id": "PR-tushare-credential",
                    "provider": "tushare",
                    "blocker_type": "credential",
                    "blocker": "TUSHARE_TOKEN is not set",
                    "review_status": "needs_review",
                    "evidence_note": "",
                    "verification_command": "python scripts\\show_provider_status.py",
                    "resolution_hint": "set token",
                    "blocks_provider_readiness": True,
                }
            ],
        }
        current_matrix = {
            "stage": "phase_4_7_provider_remediation_matrix",
            "summary": {"remediation_items": 1, "blocking_remediation_items": 1, "blocked_external_change": 1},
            "remediation_items": [
                {
                    "remediation_id": "PR-tushare-credential",
                    "provider": "tushare",
                    "blocker_type": "credential",
                    "blocker": "TUSHARE_TOKEN is not set",
                    "review_status": "blocked_external_change",
                    "evidence_note": "Tushare package is installed but token is not set",
                    "verification_command": "python scripts\\show_provider_status.py",
                    "resolution_hint": "set token",
                    "blocks_provider_readiness": True,
                }
            ],
        }

        pack = build_residual_provider_review_pack(rehearsal, provider_remediation_matrix=current_matrix)

        self.assertEqual(pack["source_stage"], "phase_4_7_provider_remediation_matrix")
        self.assertEqual(pack["summary"]["source_remediation_items"], 1)
        self.assertEqual(pack["summary"]["source_blocking_remediation_items"], 1)
        self.assertEqual(pack["residual_items"][0]["review_status"], "blocked_external_change")
        self.assertIn("token is not set", pack["residual_items"][0]["evidence_note"])


if __name__ == "__main__":
    unittest.main()
