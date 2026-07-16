import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.cn_etf_dynamic_comovement_peer_readiness import (
    REFERENCE_NAMES,
    summarize_cn_etf_dynamic_comovement_peer_readiness,
    write_cn_etf_dynamic_comovement_peer_readiness,
)
from quant_robot.research.dynamic_comovement_peer_source import DynamicPeerSourceResult


class CnEtfDynamicComovementPeerReadinessTests(unittest.TestCase):
    def test_complete_source_evidence_allows_preregistration_only(self) -> None:
        calendar, source = _ready_source()

        result = _summarize(calendar, source)

        self.assertEqual(result["status"], "ready_for_peer_source_preregistration")
        self.assertEqual(result["gate"]["blockers"], [])
        self.assertTrue(result["peer_source_preregistration_allowed"])
        self.assertFalse(result["factor_generation_allowed"])
        self.assertFalse(result["prescreen_execution_allowed"])
        self.assertEqual(result["coverage"]["qualifying_date_coverage"], 1.0)

    def test_low_date_coverage_fails_closed(self) -> None:
        calendar, source = _ready_source()

        result = _summarize(calendar, source, min_qualifying_assets_per_date=4)

        self.assertEqual(result["status"], "blocked")
        self.assertIn(
            "dynamic_peer_date_coverage_below_minimum",
            result["gate"]["blockers"],
        )

    def test_unstable_or_duplicate_source_fails_closed(self) -> None:
        calendar, source = _ready_source()
        unstable = source.stability.copy()
        unstable.loc[:, "median_jaccard"] = 0.10
        duplicate = source.duplicate_overlap.copy()
        duplicate.loc[duplicate.index[0], "edge_overlap"] = 0.50
        changed = DynamicPeerSourceResult(
            mapping=source.mapping,
            snapshots=source.snapshots,
            stability=unstable,
            duplicate_overlap=duplicate,
        )

        result = _summarize(calendar, changed)

        self.assertIn("dynamic_peer_jaccard_below_minimum", result["gate"]["blockers"])
        self.assertIn(
            "dynamic_peer_reference_overlap_above_maximum",
            result["gate"]["blockers"],
        )

    def test_source_date_leakage_is_reported_as_a_blocker(self) -> None:
        calendar, source = _ready_source()
        leaked_mapping = source.mapping.copy()
        leaked_mapping.loc[0, "source_end_date"] = leaked_mapping.loc[0, "valid_from"]
        leaked = DynamicPeerSourceResult(
            mapping=leaked_mapping,
            snapshots=source.snapshots,
            stability=source.stability,
            duplicate_overlap=source.duplicate_overlap,
        )

        result = _summarize(calendar, leaked)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("dynamic_peer_mapping_integrity_failed", result["gate"]["blockers"])
        self.assertIn("look-ahead source dates", result["mapping_integrity"]["error"])

    def test_writer_emits_all_machine_and_human_readable_artifacts(self) -> None:
        calendar, source = _ready_source()
        result = _summarize(calendar, source)

        with tempfile.TemporaryDirectory() as tmp:
            paths = write_cn_etf_dynamic_comovement_peer_readiness(
                tmp,
                result=result,
                source=source,
            )

            self.assertEqual(
                set(paths),
                {
                    "json",
                    "markdown",
                    "mapping_csv",
                    "snapshots_csv",
                    "coverage_csv",
                    "stability_csv",
                    "duplicate_csv",
                },
            )
            self.assertTrue(all(path.exists() for path in paths.values()))
            self.assertIn(
                "ready_for_peer_source_preregistration",
                paths["markdown"].read_text(encoding="utf-8"),
            )

    def test_warmup_dates_count_for_coverage_but_not_post_warmup_diagnostics(self) -> None:
        calendar, source = _ready_source()
        warmup_dates = pd.bdate_range(end=calendar[0] - pd.offsets.BDay(1), periods=2)
        expanded_calendar = warmup_dates.append(calendar)
        warmup_snapshot = source.snapshots.iloc[[0]].copy()
        warmup_snapshot.loc[:, "valid_from"] = warmup_dates[0]
        warmup_snapshot.loc[:, "valid_to"] = warmup_dates[-1]
        warmup_snapshot.loc[:, "source_end_date"] = pd.NaT
        warmup_snapshot.loc[:, "mapped_assets"] = 0
        warmup_snapshot.loc[:, "mapping_edges"] = 0
        warmup_snapshot.loc[:, "reciprocity_rate"] = 0.0
        warmup_stability = source.stability.iloc[[0]].copy()
        warmup_stability.loc[:, "previous_valid_from"] = warmup_dates[0]
        warmup_stability.loc[:, "valid_from"] = calendar[0]
        warmup_stability.loc[:, "comparable_assets"] = 0
        warmup_stability.loc[:, "median_jaccard"] = 0.0
        warmup_stability.loc[:, "median_retention"] = 0.0
        warmup_stability.loc[:, "complete_churn_rate"] = 1.0
        warmup_duplicate = source.duplicate_overlap.iloc[: len(REFERENCE_NAMES)].copy()
        warmup_duplicate.loc[:, "valid_from"] = warmup_dates[0]
        warmup_duplicate.loc[:, "edge_evidence_coverage"] = 0.0
        warmup_duplicate.loc[:, "edge_overlap"] = 1.0
        expanded_source = DynamicPeerSourceResult(
            mapping=source.mapping,
            snapshots=pd.concat([warmup_snapshot, source.snapshots], ignore_index=True),
            stability=pd.concat([warmup_stability, source.stability], ignore_index=True),
            duplicate_overlap=pd.concat(
                [warmup_duplicate, source.duplicate_overlap],
                ignore_index=True,
            ),
        )

        result = _summarize(expanded_calendar, expanded_source)

        self.assertEqual(result["status"], "ready_for_peer_source_preregistration")
        self.assertEqual(result["coverage"]["qualifying_date_coverage"], 10 / 12)
        self.assertEqual(result["stability"]["min_median_jaccard"], 1.0)
        self.assertEqual(result["duplicate_overlap"]["min_edge_evidence_coverage"], 1.0)
        self.assertEqual(result["duplicate_overlap"]["max_edge_overlap"], 0.0)

    def test_daily_coverage_requires_asset_and_minimum_peers_to_remain_eligible(self) -> None:
        calendar, source = _ready_source()
        daily_eligible_keys = pd.DataFrame(
            [
                {"date": signal_date, "asset_id": asset_id}
                for signal_date in calendar
                for asset_id in ("A", "B")
            ]
        )

        result = summarize_cn_etf_dynamic_comovement_peer_readiness(
            calendar_dates=calendar,
            source=source,
            daily_eligible_keys=daily_eligible_keys,
            min_active_peers_per_asset=2,
            min_qualifying_assets_per_date=2,
            min_qualifying_date_coverage=0.80,
            min_comparable_assets_per_transition=2,
            min_median_jaccard=0.25,
            min_median_retention=0.40,
            max_complete_churn_rate=0.40,
            min_reciprocity_rate=0.30,
            max_reference_edge_overlap=0.50,
            min_reference_edge_coverage=0.80,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["coverage"]["qualifying_dates"], 0)
        self.assertIn(
            "dynamic_peer_date_coverage_below_minimum",
            result["gate"]["blockers"],
        )


def _summarize(
    calendar: pd.DatetimeIndex,
    source: DynamicPeerSourceResult,
    *,
    min_qualifying_assets_per_date: int = 2,
) -> dict:
    return summarize_cn_etf_dynamic_comovement_peer_readiness(
        calendar_dates=calendar,
        source=source,
        min_qualifying_assets_per_date=min_qualifying_assets_per_date,
        min_qualifying_date_coverage=0.80,
        min_comparable_assets_per_transition=2,
        min_median_jaccard=0.25,
        min_median_retention=0.40,
        max_complete_churn_rate=0.40,
        min_reciprocity_rate=0.30,
        max_reference_edge_overlap=0.50,
        min_reference_edge_coverage=0.80,
    )


def _ready_source() -> tuple[pd.DatetimeIndex, DynamicPeerSourceResult]:
    calendar = pd.bdate_range("2024-01-02", periods=10)
    first_valid = calendar[0]
    second_valid = calendar[5]
    intervals = [
        (first_valid, calendar[4], pd.Timestamp("2023-12-29")),
        (second_valid, calendar[-1], calendar[4]),
    ]
    mapping_rows = []
    peers = {
        "A": ["B", "C"],
        "B": ["A", "C"],
        "C": ["A", "B"],
    }
    for valid_from, valid_to, source_end in intervals:
        for asset_id, peer_ids in peers.items():
            for rank, peer_id in enumerate(peer_ids, start=1):
                mapping_rows.append(
                    {
                        "asset_id": asset_id,
                        "peer_asset_id": peer_id,
                        "valid_from": valid_from,
                        "valid_to": valid_to,
                        "known_from": valid_from,
                        "source_end_date": source_end,
                        "similarity": 0.75,
                        "pair_observations": 80,
                        "peer_rank": rank,
                        "peer_count": 2,
                        "mapping_method": "lagged_market_residual_correlation_topk",
                        "source": "fixture",
                    }
                )
    snapshots = pd.DataFrame(
        [
            {
                "valid_from": valid_from,
                "valid_to": valid_to,
                "source_end_date": source_end,
                "eligible_assets": 3,
                "return_ready_assets": 3,
                "residual_ready_assets": 3,
                "mapped_assets": 3,
                "mapping_edges": 6,
                "reciprocity_rate": 1.0,
                "median_selected_similarity": 0.75,
            }
            for valid_from, valid_to, source_end in intervals
        ]
    )
    stability = pd.DataFrame(
        [
            {
                "previous_valid_from": first_valid,
                "valid_from": second_valid,
                "comparable_assets": 3,
                "median_jaccard": 1.0,
                "median_retention": 1.0,
                "complete_churn_rate": 0.0,
            }
        ]
    )
    duplicate_rows = []
    for valid_from in (first_valid, second_valid):
        for reference_name in REFERENCE_NAMES:
            duplicate_rows.append(
                {
                    "valid_from": valid_from,
                    "reference_name": reference_name,
                    "selected_edges": 6,
                    "evidence_edges": 6,
                    "common_edges": 0,
                    "edge_evidence_coverage": 1.0,
                    "edge_overlap": 0.0,
                }
            )
    return calendar, DynamicPeerSourceResult(
        mapping=pd.DataFrame(mapping_rows),
        snapshots=snapshots,
        stability=stability,
        duplicate_overlap=pd.DataFrame(duplicate_rows),
    )


if __name__ == "__main__":
    unittest.main()
