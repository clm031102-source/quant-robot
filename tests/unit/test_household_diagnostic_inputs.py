import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.research.household_diagnostic_inputs import (
    check_source_links, source_reports, source_schedule, calculate_from_snapshots,
)
from quant_robot.research.monthly_diagnostic_registration import canonical
from tests.unit.household_diagnostic_fixtures import execution_fixture


class HouseholdInputTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.packet, _, _, self.snapshots = execution_fixture(self.root)

    def test_link_check_decodes_no_prices_or_real_signals(self):
        with patch('pandas.read_parquet', side_effect=AssertionError('no prices')), \
                patch('quant_robot.research.household_diagnostic_inputs.annual_preference_gate', side_effect=AssertionError('no signal')):
            check_source_links(self.packet, self.snapshots)

    def test_all_source_and_visual_links_are_required(self):
        for role, field in [('source_review', 'source_inventory_sha256'),
                ('visual_review', 'source_inventory_sha256'), ('timing_review', 'calendar_sha256')]:
            snapshots = copy.deepcopy(self.snapshots); value = json.loads(snapshots[role]); value[field] = '0'*64
            snapshots[role] = canonical(value)
            with self.subTest(role=role), self.assertRaises(ValueError): check_source_links(self.packet, snapshots)

    def test_missing_or_duplicate_quarters_are_rejected(self):
        for duplicate in (False, True):
            value = json.loads(self.snapshots['survey_inventory']); value['rows'].pop()
            if duplicate: value['rows'].append(value['rows'][0])
            snapshots = self.snapshots | {'survey_inventory': canonical(value)}
            with self.assertRaises(ValueError): source_reports(self.packet, snapshots)

    def test_stock_value_must_match_selected_label_and_visual_review(self):
        value = json.loads(self.snapshots['survey_inventory']); value['rows'][0]['stock_preference_pct'] = '40'
        with self.assertRaises(ValueError): source_reports(self.packet, self.snapshots | {'survey_inventory': canonical(value)})

    def test_unverified_historical_claim_cannot_turn_itself_into_certification(self):
        value = json.loads(self.snapshots['source_review']); value['source_audit_verified'] = True
        with self.assertRaises(ValueError): check_source_links(self.packet, self.snapshots | {'source_review': canonical(value)})

    def test_calendar_maps_joint_release_to_one_latest_quarter(self):
        reports = source_reports(self.packet, self.snapshots)
        sessions, anchors, intervals = source_schedule(self.packet, self.snapshots, reports)
        self.assertEqual(len(sessions), 1069); self.assertEqual(len(anchors), 18); self.assertEqual(len(intervals), 17)
        self.assertNotIn('2023Q3', [r['latest_visible_report_quarter'] for r in intervals])
        self.assertIn('2023Q4', [r['latest_visible_report_quarter'] for r in intervals])

    def test_altered_frozen_anchor_is_not_silently_recomputed(self):
        value = json.loads(self.snapshots['timing_review']); value['intervals'][0]['end'] = '2020-04-20'
        snapshots = self.snapshots | {'timing_review': canonical(value)}
        with self.assertRaises(ValueError): source_schedule(self.packet, snapshots, source_reports(self.packet, snapshots))

    def test_complete_synthetic_pipeline_has_zero_gross_edge_and_no_account_claim(self):
        result = calculate_from_snapshots(self.packet, self.snapshots)
        self.assertEqual(result['diagnostic']['interval_count'], 17)
        self.assertEqual(len(result['intervals']), 17)
        self.assertEqual(result['diagnostic']['decision'], 'reject_fixed_diagnostic')
        self.assertFalse(result['net_account_result']); self.assertFalse(result['formal_positive_ev_verified'])
        self.assertEqual(result['counts_as_forward_paper_days'], 0)


if __name__ == '__main__': unittest.main()
