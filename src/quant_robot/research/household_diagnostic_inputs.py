"""Decode the fixed study's verified snapshots; never fetch or reopen sources."""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from decimal import Context, Decimal, localcontext
import io
import json
from pathlib import Path
import re
import tempfile

import pandas as pd

from quant_robot.research.household_diagnostic_registration import HYPOTHESIS, QUARTERS
from quant_robot.research.household_preference_diagnostic import (
    SurveyObservation, annual_preference_gate, visible_annual_window, event_log_selection_diagnostic,
)
from quant_robot.research.price_basis import build_cash_action_research_prices

PROPOSAL_SHA256 = '888369cdcfaf0f57101485a7db88d7d455503201c86b79e175b75497640e4c91'
ASSET = 'CN_ETF_XSHG_510300'


def _rows_by_quarter(rows):
    if not isinstance(rows, list) or len(rows) != 22 or any(not isinstance(r, dict) for r in rows):
        raise ValueError('exactly 22 source rows are required')
    mapped = {row.get('quarter'): row for row in rows}
    if set(mapped) != set(QUARTERS):
        raise ValueError('source quarters are missing, duplicate, or outside the fixed window')
    return mapped


def _available_day(row):
    published = datetime.strptime(row['detail_time'], '%Y-%m-%d %H:%M:%S')
    if published.strftime('%Y-%m-%d %H:%M:%S') != row['detail_time']:
        raise ValueError('article timestamp must retain its explicit precision')
    catalog = date.fromisoformat(row['catalog_date'])
    if published.date() != catalog:
        raise ValueError('catalog and article publication dates differ')
    candidates = row['pdf_date_candidates']
    if not isinstance(candidates, list) or len(candidates) > 1:
        raise ValueError('PDF declared date needs unambiguous review')
    days = [catalog, published.date()]
    for token in candidates:
        match = re.fullmatch(r'([0-9]{4})年([0-9]{1,2})月([0-9]{1,2})日', token)
        if match is None:
            raise ValueError('PDF date token not understood')
        days.append(date(*map(int, match.groups())))
    return max(days) + timedelta(days=1)


def source_reports(packet, snapshots):
    """Validate source/visual correspondence, retaining assumed availability."""
    try:
        inventory = json.loads(snapshots['survey_inventory'])
        visual = json.loads(snapshots['visual_review'])
        rows, verified = _rows_by_quarter(inventory['rows']), _rows_by_quarter(visual['rows'])
        if inventory.get('failed') != [] or inventory.get('unextracted') != []:
            raise ValueError('source inventory has unresolved reports')
        reports = []
        for quarter in QUARTERS:
            row, seen = rows[quarter], verified[quarter]
            pdf_sha = packet['inputs']['survey_pdf_' + quarter]['sha256']
            article_sha = packet['inputs']['survey_article_' + quarter]['sha256']
            if (row['success'] is not True or row['sha256'] != pdf_sha or row['detail_sha256'] != article_sha
                    or seen['pdf_sha256'] != pdf_sha or seen['visual_verified'] is not True
                    or seen['physical_page'] != 2 or row['pages'] != 4):
                raise ValueError('source PDF, article, and visual verification differ')
            if (row['preference_sentence_count'] != 1 or row['preference_labels'] !=
                    ['银行、证券、保险公司理财产品', '基金信托产品', '股票']
                    or len(row['preference_values_pct']) != 3):
                raise ValueError('stock preference definition changed or is ambiguous')
            value = row['stock_preference_pct']
            if (not isinstance(value, str) or value != row['preference_values_pct'][2]
                    or value != seen['stock_preference_pct']):
                raise ValueError('stock percentage differs from label or visual review')
            number = Decimal(value)
            if not number.is_finite() or not 0 <= number <= 100:
                raise ValueError('stock preference percentage must be within 0..100')
            if datetime.fromisoformat(row['observed_at']).tzinfo is None:
                raise ValueError('actual observation timestamp must retain timezone')
            reports.append(SurveyObservation(quarter, _available_day(row), value))
        return reports
    except (KeyError, TypeError, IndexError, ArithmeticError) as exc:
        raise ValueError('source report fields missing or malformed') from exc


def check_source_links(packet, snapshots):
    """Input byte hashes are checked by preflight before this metadata-only step."""
    inputs = packet['inputs']
    proposal = json.loads(snapshots['proposal'])
    if packet['source_origin'] == 'retained_research_sources' and inputs['proposal']['sha256'] != PROPOSAL_SHA256:
        raise ValueError('real inputs require the frozen household proposal')
    if proposal.get('economic_hypothesis_id') != HYPOTHESIS:
        raise ValueError('economic hypothesis differs from registration')
    review = json.loads(snapshots['source_review'])
    if (review.get('status') != 'conditional_historical_source_use_reviewed_not_execution_admission'
            or review.get('economic_hypothesis_id') != HYPOTHESIS):
        raise ValueError('conditional household source-use review required')
    for field in ('historical_availability_verified', 'source_audit_verified', 'research_admission_granted', 'factor_or_return_computed'):
        if review.get(field) is not False:
            raise ValueError('source review cannot confer certification or execution authority')
    for field, role in (('proposal_sha256', 'proposal'), ('source_inventory_sha256', 'survey_inventory'),
            ('visual_verification_sha256', 'visual_review'), ('timing_review_sha256', 'timing_review'),
            ('retained_price_action_join_sha256', 'source_join')):
        if review.get(field) != inputs[role]['sha256']:
            raise ValueError('source-use evidence identity differs: ' + role)
    fingerprints = review.get('freshly_verified_public_document_fingerprints', {})
    if review.get('freshly_verified_public_document_count') != 48 or len(fingerprints) != 48:
        raise ValueError('all 48 reviewed public documents required')
    for role, record in inputs.items():
        if not role.startswith(('survey_pdf_', 'survey_article_', 'survey_catalog_')):
            continue
        matches = [digest for path, digest in fingerprints.items()
            if path.replace('\\', '/') == record['path'] or path.replace('\\', '/').endswith('/' + record['path'])]
        if matches != [record['sha256']]:
            raise ValueError('public source fingerprint differs: ' + role)
    visual = json.loads(snapshots['visual_review'])
    if visual.get('source_inventory_sha256') != inputs['survey_inventory']['sha256'] or visual.get('verified_reports') != 22:
        raise ValueError('visual review must bind the original 22-report inventory')
    timing = json.loads(snapshots['timing_review'])
    if (timing.get('source_inventory_sha256') != inputs['survey_inventory']['sha256']
            or timing.get('calendar_sha256') != inputs['calendar']['sha256']
            or proposal['source_use']['calendar_sha256'] != inputs['calendar']['sha256']):
        raise ValueError('source timing and calendar identities differ')
    joined = json.loads(snapshots['source_join'])
    hashes = {path.replace('\\', '/'): digest for path, digest in joined.get('fingerprints', {}).items()}
    for role in ('calendar', 'actions', *['bars_' + str(year) for year in range(2020, 2025)]):
        if hashes.get(inputs[role]['path']) != inputs[role]['sha256']:
            raise ValueError('price/action component identity differs: ' + role)
    reports = source_reports(packet, snapshots)
    source_schedule(packet, snapshots, reports)


def source_schedule(packet, snapshots, reports):
    first, terminal = date(2020, 1, 2), date(2024, 6, 3)
    rows = list(csv.DictReader(io.StringIO(snapshots['calendar'].decode('utf-8-sig'))))
    calendar = [r for r in rows if r['market'] == 'CN' and str(first) <= r['date'] <= str(terminal)]
    if (len({r['date'] for r in calendar}) != len(calendar)
            or any(r['is_open'] not in ('0', '1') for r in calendar)):
        raise ValueError('calendar dates duplicate or open markers invalid')
    sessions = sorted(date.fromisoformat(r['date']) for r in calendar if r['is_open'] == '1')
    if len(sessions) != 1069 or sessions[0] != first or sessions[-1] != terminal:
        raise ValueError('complete frozen 1069-session calendar required')
    anchors = {first, terminal}
    for report in reports:
        if first < report.available_on < terminal:
            anchors.add(next(s for s in sessions if s >= report.available_on))
    anchors = sorted(anchors)
    if len(anchors) != 18:
        raise ValueError('source publications must produce exactly 18 anchors')
    inventory = _rows_by_quarter(json.loads(snapshots['survey_inventory'])['rows'])
    expected_rows = [{'quarter': r.quarter, 'quarter_number': int(r.quarter[:4])*4+int(r.quarter[-1])-1,
        'assumed_available_day': r.available_on.isoformat(), 'source_pdf_sha256': inventory[r.quarter]['sha256'],
        'detail_sha256': inventory[r.quarter]['detail_sha256']} for r in reports]
    timing = json.loads(snapshots['timing_review'])
    if timing.get('source_rows') != expected_rows:
        raise ValueError('reviewed source availability dates differ')
    positions = {s: i for i, s in enumerate(sessions)}
    intervals = []
    for start, end in zip(anchors, anchors[1:]):
        visible = visible_annual_window(reports, start)
        quarters = list(visible)
        intervals.append({'start': str(start), 'end': str(end),
            'close_to_close_transitions': positions[end]-positions[start],
            'latest_visible_report_quarter': quarters[-1], 'required_report_quarters': quarters,
            'source_pdf_sha256': [inventory[q]['sha256'] for q in quarters]})
    if (timing.get('intervals') != intervals or timing.get('anchor_count') != 18
            or timing.get('interval_count') != 17 or timing.get('close_to_close_transition_count') != 1068):
        raise ValueError('frozen source schedule differs; do not silently recompute another study')
    return sessions, anchors, intervals


def calculate_from_snapshots(packet, snapshots):
    """Caller must durably claim the new study before entering this function."""
    reports = source_reports(packet, snapshots)
    sessions, anchors, intervals = source_schedule(packet, snapshots, reports)
    windows = [visible_annual_window(reports, anchor) for anchor in anchors[:-1]]
    signals = [annual_preference_gate(window) for window in windows]
    frames = []
    for year in range(2020, 2025):
        frame = pd.read_parquet(io.BytesIO(snapshots['bars_' + str(year)]), engine='pyarrow',
            columns=['date', 'asset_id', 'market', 'currency', 'close'],
            filters=[('asset_id', '==', ASSET), ('date', '>=', pd.Timestamp(sessions[0])),
                ('date', '<=', pd.Timestamp(sessions[-1]))])
        if not frame.empty and not pd.to_datetime(frame['date']).dt.year.eq(year).all():
            raise ValueError('bar content does not match declared year')
        frames.append(frame)
    bars = pd.concat(frames, ignore_index=True)
    with tempfile.TemporaryDirectory(prefix='household-diagnostic-') as temporary:
        path = Path(temporary) / 'verified-actions.json'
        path.write_bytes(snapshots['actions'])
        prices = build_cash_action_research_prices(bars, path, sessions=sessions)
    if prices.evidence['cash_amount_basis'] not in {'gross', 'no_cash_events'}:
        raise ValueError('fixed diagnostic requires gross cash observations')
    indexed = prices.bars.set_index('date')['adj_close']
    levels = [indexed.loc[anchor] for anchor in anchors]
    diagnostic = event_log_selection_diagnostic(anchors, signals, levels, sessions)
    with localcontext(Context(prec=64)):
        details = [{**row, 'signal': signals[i], 'survey_values': {q: str(v) for q, v in windows[i].items()},
            'analytical_log_return': str((Decimal(str(levels[i+1])) / Decimal(str(levels[i]))).ln())}
            for i, row in enumerate(intervals)]
    return {'stage': packet['stage'], 'registration_id': packet['registration_id'],
        'economic_hypothesis_id': HYPOTHESIS, 'source_origin': packet['source_origin'],
        'diagnostic': diagnostic, 'intervals': details, 'analytical_price_evidence': prices.evidence,
        'historical_version_assumption_verified': False, 'source_audit_verified': False,
        'net_account_result': False, 'qualifies_for_promotion': False,
        'counts_as_forward_paper_days': 0, 'formal_positive_ev_verified': False,
        'signal_ones': sum(signals), 'signal_zeros': len(signals)-sum(signals)}
