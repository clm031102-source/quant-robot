import unittest

from quant_robot.ops.duplicate_registry import build_duplicate_registry


class DuplicateRegistryTests(unittest.TestCase):
    def test_registry_records_canonical_candidates_and_suppressed_duplicates(self):
        promotion_report = {
            "candidates": [
                {
                    "promotion_rank": 1,
                    "case_id": "canonical_a",
                    "market": "CN_ETF",
                    "factor_name": "liquidity_10",
                    "promotion_status": "paper_ready",
                    "score": 42.0,
                    "duplicate_of": None,
                    "duplicate_similarity": 0.0,
                    "blocking_reasons": [],
                    "warnings": [],
                },
                {
                    "promotion_rank": 2,
                    "case_id": "duplicate_b",
                    "market": "CN_ETF",
                    "factor_name": "liquidity_20",
                    "promotion_status": "blocked",
                    "score": 0.0,
                    "duplicate_of": "canonical_a",
                    "duplicate_similarity": 0.99,
                    "blocking_reasons": ["duplicate_signal_candidate"],
                    "warnings": ["duplicate_of:canonical_a"],
                },
                {
                    "promotion_rank": 3,
                    "case_id": "standalone_c",
                    "market": "CN_ETF",
                    "factor_name": "momentum_20",
                    "promotion_status": "blocked",
                    "score": 0.0,
                    "duplicate_of": None,
                    "duplicate_similarity": 0.0,
                    "blocking_reasons": ["walk_forward_not_accepted"],
                    "warnings": [],
                },
            ]
        }

        registry = build_duplicate_registry(promotion_report)

        self.assertEqual(registry["stage"], "phase_3_4_duplicate_canonical_registry")
        self.assertEqual(registry["summary"]["canonical_candidates"], 2)
        self.assertEqual(registry["summary"]["duplicate_members"], 1)
        self.assertEqual(registry["summary"]["clusters"], 1)
        canonical = {row["canonical_case_id"]: row for row in registry["canonical_registry"]}
        self.assertEqual(canonical["canonical_a"]["duplicate_count"], 1)
        self.assertEqual(canonical["standalone_c"]["duplicate_count"], 0)
        duplicate = registry["duplicate_members"][0]
        self.assertEqual(duplicate["duplicate_case_id"], "duplicate_b")
        self.assertEqual(duplicate["canonical_case_id"], "canonical_a")
        self.assertEqual(duplicate["suppression_reason"], "duplicate_signal_candidate")
        self.assertIn("canonical_a", registry["markdown"])


if __name__ == "__main__":
    unittest.main()
