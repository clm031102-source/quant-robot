import unittest

from quant_robot.ops.provider_remediation import (
    build_provider_remediation_matrix,
    build_review_template_rows,
    remediation_status_options,
)


class ProviderRemediationTests(unittest.TestCase):
    def test_matrix_turns_provider_evidence_into_local_remediation_items(self):
        evidence = {
            "stage": "phase_3_2_provider_readiness_evidence",
            "providers": [
                {
                    "provider": "tushare",
                    "ready": False,
                    "readiness_status": "missing_dependency_and_token",
                    "package": "tushare",
                    "credential": "TUSHARE_TOKEN",
                    "missing": ["tushare package is not installed", "TUSHARE_TOKEN is not set"],
                },
                {
                    "provider": "akshare",
                    "ready": False,
                    "readiness_status": "planned_adapter",
                    "package": "akshare",
                    "credential": None,
                    "missing": ["adapter implementation is planned"],
                },
            ],
            "parquet": {"ready": False, "missing": ["pyarrow or fastparquet package is not installed"]},
        }

        matrix = build_provider_remediation_matrix(evidence)

        self.assertEqual(matrix["stage"], "phase_4_7_provider_remediation_matrix")
        self.assertEqual(matrix["summary"]["remediation_items"], 4)
        self.assertEqual(matrix["summary"]["dependency_items"], 1)
        self.assertEqual(matrix["summary"]["credential_items"], 1)
        self.assertEqual(matrix["summary"]["adapter_items"], 1)
        self.assertEqual(matrix["summary"]["storage_items"], 1)
        items = {(row["provider"], row["blocker_type"]): row for row in matrix["remediation_items"]}
        self.assertIn("tushare", items[("tushare", "dependency")]["resolution_hint"])
        self.assertIn("TUSHARE_TOKEN", items[("tushare", "credential")]["resolution_hint"])
        self.assertEqual(items[("akshare", "adapter_implementation")]["verification_command"], "python scripts\\show_provider_status.py")
        self.assertTrue(items[("parquet", "storage_dependency")]["blocks_provider_readiness"])
        self.assertIn("No broker", matrix["safety"])
        self.assertIn("tushare", matrix["markdown"])

    def test_review_template_rows_preserve_remediation_items_and_status_guidance(self):
        evidence = {
            "providers": [
                {
                    "provider": "tushare",
                    "ready": False,
                    "package": "tushare",
                    "credential": "TUSHARE_TOKEN",
                    "missing": ["tushare package is not installed"],
                }
            ],
            "parquet": {"ready": True, "missing": []},
        }

        matrix = build_provider_remediation_matrix(evidence)
        rows = build_review_template_rows(matrix)
        options = {row["review_status"]: row for row in remediation_status_options()}

        self.assertEqual(rows[0]["remediation_id"], "PR-tushare-dependency")
        self.assertEqual(rows[0]["provider"], "tushare")
        self.assertEqual(rows[0]["review_status"], "needs_review")
        self.assertIn("resolved_locally", rows[0]["allowed_statuses"])
        self.assertIn("review_guidance", rows[0])
        self.assertTrue(options["needs_review"]["blocks_provider_readiness"])
        self.assertFalse(options["resolved_locally"]["blocks_provider_readiness"])

    def test_matrix_validates_and_applies_review_rows(self):
        evidence = {
            "providers": [
                {
                    "provider": "tushare",
                    "ready": False,
                    "package": "tushare",
                    "credential": "TUSHARE_TOKEN",
                    "missing": ["tushare package is not installed"],
                },
                {
                    "provider": "ccxt",
                    "ready": False,
                    "package": "ccxt",
                    "missing": ["ccxt package is not installed"],
                },
            ],
            "parquet": {"ready": True, "missing": []},
        }
        review_rows = [
            {
                "remediation_id": "PR-tushare-dependency",
                "review_status": "resolved_locally",
                "evidence_note": "Installed package in local research environment and reran readiness checks.",
                "reviewed_by": "local-reviewer",
                "reviewed_at": "2026-06-01T00:00:00Z",
            },
            {"remediation_id": "PR-unknown-dependency", "review_status": "resolved_locally"},
            {"remediation_id": "PR-tushare-dependency", "review_status": "accepted_out_of_scope"},
            {"remediation_id": "PR-ccxt-dependency", "review_status": "not_a_status"},
        ]

        matrix = build_provider_remediation_matrix(evidence, review_rows=review_rows)

        items = {row["remediation_id"]: row for row in matrix["remediation_items"]}
        self.assertEqual(matrix["review_validation"]["summary"]["applied_review_rows"], 1)
        self.assertEqual(matrix["review_validation"]["summary"]["validation_errors"], 3)
        self.assertEqual(matrix["summary"]["blocking_remediation_items"], 1)
        self.assertEqual(matrix["summary"]["resolved_locally"], 1)
        self.assertEqual(matrix["summary"]["needs_review"], 1)
        self.assertFalse(items["PR-tushare-dependency"]["blocks_provider_readiness"])
        self.assertEqual(items["PR-tushare-dependency"]["review_status"], "resolved_locally")
        self.assertIn("Installed package", items["PR-tushare-dependency"]["evidence_note"])
        self.assertTrue(items["PR-ccxt-dependency"]["blocks_provider_readiness"])


if __name__ == "__main__":
    unittest.main()
