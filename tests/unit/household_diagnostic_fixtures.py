"""Synthetic household study inputs, including an explicitly synthetic calendar."""
from datetime import date, datetime, timedelta, timezone
import io

import pandas as pd

from quant_robot.research.household_diagnostic_registration import (
    DIRECTORY, HYPOTHESIS, QUARTERS, build_registration, expected_input_paths,
)
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256
from tests.unit.test_household_diagnostic_registration import scheduler_fixture


def execution_fixture(root):
    paths = expected_input_paths(); inputs = {}; snapshots = {}
    def put(role, value):
        content = value if isinstance(value, bytes) else canonical(value)
        path = root / paths[role]; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content); snapshots[role] = content
        inputs[role] = {'path': paths[role], 'sha256': sha256(content)}

    first, terminal = date(2020, 1, 2), date(2024, 6, 3)
    span = (terminal-first).days
    sessions = [first+timedelta(days=span*i//1068) for i in range(1069)]
    put('calendar', pd.DataFrame({'market': 'CN', 'date': sessions, 'is_open': 1,
                                  'source': 'synthetic, not an exchange calendar'}).to_csv(index=False).encode())
    put('actions', {'schema_version': 3, 'source_ref': 'synthetic fixture', 'asset_ids': ['CN_ETF_XSHG_510300'],
                    'coverage_start': str(first), 'coverage_end': str(terminal), 'events': []})
    for year in range(2020, 2025):
        dates = [d for d in sessions if d.year == year]
        frame = pd.DataFrame({'date': dates, 'asset_id': 'CN_ETF_XSHG_510300',
                              'market': 'CN_ETF', 'currency': 'CNY', 'close': 10.0})
        stream = io.BytesIO(); frame.to_parquet(stream, index=False); put('bars_'+str(year), stream.getvalue())
    for role in paths:
        if role.startswith(('survey_pdf_', 'survey_article_', 'survey_catalog_')):
            put(role, ('synthetic original '+role).encode())
    rows, visual, timing_rows = [], [], []
    for i, quarter in enumerate(QUARTERS):
        year, q = int(quarter[:4]), int(quarter[-1])
        next_q = date(year+1, 1, 1) if q == 4 else date(year, q*3+1, 1)
        published = next_q-timedelta(days=1)
        if quarter in ('2023Q3', '2023Q4'): published = date(2024, 3, 22)
        available = published+timedelta(days=1)
        value = str(10+i%3)
        pdf = inputs['survey_pdf_'+quarter]['sha256']; article = inputs['survey_article_'+quarter]['sha256']
        rows.append({'quarter': quarter, 'success': True, 'sha256': pdf,
            'detail_sha256': article, 'pages': 4, 'catalog_date': str(published),
            'detail_time': str(published)+' 16:00:00',
            'pdf_date_candidates': [f'{published.year}年{published.month}月{published.day}日'],
            'stock_preference_pct': value, 'preference_sentence_count': 1,
            'preference_labels': ['银行、证券、保险公司理财产品', '基金信托产品', '股票'],
            'preference_values_pct': ['40', '20', value],
            'observed_at': '2026-09-14T00:00:00+00:00'})
        visual.append({'quarter': quarter, 'pdf_sha256': pdf, 'physical_page': 2,
            'stock_preference_pct': value, 'visual_verified': True})
        timing_rows.append({'quarter': quarter, 'quarter_number': year*4+q-1,
            'assumed_available_day': str(available), 'source_pdf_sha256': pdf, 'detail_sha256': article})
    put('survey_inventory', {'rows': rows, 'failed': [], 'unextracted': [],
        'source_authority_verified': False, 'factor_allowed': False, 'ETF_outcomes_read': False})
    put('visual_review', {'source_inventory_sha256': inputs['survey_inventory']['sha256'],
        'rows': visual, 'verified_reports': 22, 'historical_availability_verified': False, 'factor_generation_allowed': False})
    anchors = {first, terminal}
    for row in timing_rows:
        available = date.fromisoformat(row['assumed_available_day'])
        if first < available < terminal:
            anchors.add(next(s for s in sessions if s >= available))
    anchors = sorted(anchors); assert len(anchors) == 18
    intervals = []
    for start, end in zip(anchors, anchors[1:]):
        available = [r for r in timing_rows if r['assumed_available_day'] <= str(start)]
        latest = max(r['quarter_number'] for r in available)
        selected = [r for r in available if latest-4 <= r['quarter_number'] <= latest]
        intervals.append({'start': str(start), 'end': str(end),
            'close_to_close_transitions': sessions.index(end)-sessions.index(start),
            'latest_visible_report_quarter': selected[-1]['quarter'],
            'required_report_quarters': [r['quarter'] for r in selected],
            'source_pdf_sha256': [r['source_pdf_sha256'] for r in selected]})
    put('proposal', {'economic_hypothesis_id': HYPOTHESIS,
        'window': {'first_anchor': str(first), 'terminal_anchor': str(terminal),
            'expected_anchor_count': 18, 'expected_interval_count': 17,
            'expected_close_to_close_transition_count': 1068},
        'source_use': {'calendar_sha256': inputs['calendar']['sha256']}})
    put('timing_review', {'proposal_sha256': inputs['proposal']['sha256'],
        'source_inventory_sha256': inputs['survey_inventory']['sha256'],
        'calendar_sha256': inputs['calendar']['sha256'], 'source_rows': timing_rows,
        'anchor_count': 18, 'interval_count': 17, 'close_to_close_transition_count': 1068,
        'intervals': intervals, 'source_historical_version_assumption_verified': False,
        'factor_computed': False, 'ETF_outcome_read': False, 'admission_granted': False})
    price_roles = ['calendar', 'actions', *['bars_'+str(y) for y in range(2020, 2025)]]
    put('source_join', {'fingerprints': {inputs[r]['path']: inputs[r]['sha256'] for r in price_roles}})
    put('source_review', {'status': 'conditional_historical_source_use_reviewed_not_execution_admission',
        'economic_hypothesis_id': HYPOTHESIS, 'proposal_sha256': inputs['proposal']['sha256'],
        'source_inventory_sha256': inputs['survey_inventory']['sha256'],
        'visual_verification_sha256': inputs['visual_review']['sha256'],
        'timing_review_sha256': inputs['timing_review']['sha256'],
        'retained_price_action_join_sha256': inputs['source_join']['sha256'],
        'freshly_verified_public_document_count': 48,
        'freshly_verified_public_document_fingerprints': {inputs[r]['path']: inputs[r]['sha256']
            for r in inputs if r.startswith(('survey_pdf_', 'survey_article_', 'survey_catalog_'))},
        'historical_availability_verified': False, 'source_audit_verified': False,
        'research_admission_granted': False, 'factor_or_return_computed': False})
    code = root/'household_fixture.py'; code.write_bytes(b'# synthetic fixture\n')
    packet = build_registration(inputs=inputs, code_files={code.name: sha256(code.read_bytes())},
        environment={'python': 'fixture'}, source_origin='synthetic_fixture', branch='codex/factor-review-fixture')
    path = root/DIRECTORY/'registration.json'; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(canonical(packet))
    scheduler = scheduler_fixture(packet)
    gate = {'status': 'ready', 'mode': 'single_household_diagnostic_only',
        'generated_at': datetime.now(timezone.utc).isoformat(), 'primary_market': 'CN_ETF', 'blockers': [],
        'selected': {'machine': 'office_desktop', 'task': 'factor_batch',
            'branch': packet['branch'], 'current_branch': packet['branch']},
        'safety': {'factor_batch_allowed': False, 'factor_batch_scope': {},
            'monthly_diagnostic_allowed': False, 'household_diagnostic_allowed': True,
            'household_diagnostic_scope': scheduler['household_diagnostic_decision'],
            'final_holdout_allowed': False, 'live_boundary_allowed': False}}
    return packet, scheduler, gate, snapshots
