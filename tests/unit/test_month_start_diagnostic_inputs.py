import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.research.month_start_diagnostic_inputs import check_source_links
from quant_robot.research.monthly_diagnostic_registration import canonical
from tests.unit.month_start_diagnostic_fixtures import execution_fixture


class MonthStartInputTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.packet,_,_,self.snapshots=execution_fixture(Path(temporary.name))

    def test_source_review_is_metadata_only(self):
        with patch('pandas.read_parquet',side_effect=AssertionError('no outcomes')), \
                patch('quant_robot.research.month_start_diagnostic_inputs.month_start_diagnostic',
                      side_effect=AssertionError('no positions or returns')):
            check_source_links(self.packet,self.snapshots)

    def test_certification_or_old_study_identity_cannot_replace_new_review(self):
        for change in ({'source_audit_verified':True}, {'research_admission_granted':True},
                       {'economic_hypothesis_id':'household_equity_preference_annual_contrast_v1'},
                       {'real_calendar_positions_generated':True}, {'open_session_count':1068}):
            snapshots=dict(self.snapshots)
            snapshots['source_review']=canonical({**json.loads(snapshots['source_review']),**change})
            with self.subTest(change=change),self.assertRaises(ValueError):
                check_source_links(self.packet,snapshots)

    def test_component_or_reviewed_input_mismatch_is_rejected(self):
        for role in ('calendar_manifest','actions','bars_2020'):
            packet=copy.deepcopy(self.packet);packet['inputs'][role]['sha256']='0'*64
            with self.subTest(role=role),self.assertRaises(ValueError):
                check_source_links(packet,self.snapshots)

    def test_real_origin_cannot_select_a_changed_proposal(self):
        packet=copy.deepcopy(self.packet);packet['source_origin']='retained_research_sources'
        packet['inputs']['proposal']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'frozen month-start proposal'):
            check_source_links(packet,self.snapshots)

    def test_calendar_bytes_are_checked_against_the_declared_source(self):
        snapshots=dict(self.snapshots);snapshots['calendar']+=b'corrupted'
        with self.assertRaises(ValueError):check_source_links(self.packet,snapshots)
