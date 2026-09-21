"""Decode only a claimed study's verified byte snapshots; no network access."""
from __future__ import annotations

import csv
from datetime import date, timedelta
from decimal import Decimal
import io
import json
from pathlib import Path
import tempfile

import pandas as pd

from quant_robot.data.alfred_monthly_vintages import parse_alfred_monthly_vintages
from quant_robot.research.policy_uncertainty_diagnostic import monthly_median_gate, monthly_selection_diagnostic
from quant_robot.research.price_basis import build_cash_action_research_prices

PROPOSAL_SHA256 = '35aa153c60414d12a40b23ece7446aaea9334171c549be1927bb6adf980d586d'
ASSET = 'CN_ETF_XSHG_510300'
SERIES = 'CHNMAINLANDEPU'


def check_source_links(packet, snapshots):
    inputs = packet['inputs']
    if inputs['proposal']['sha256'] != PROPOSAL_SHA256:
        raise ValueError('historical diagnostic proposal is not the frozen proposal')
    review = json.loads(snapshots['source_review'])
    if review.get('status') != 'conditional_analytical_use_review_complete_not_execution_admission':
        raise ValueError('conditional source-use review missing')
    for field, role in (('proposal_sha256', 'proposal'), ('retained_joint_audit_sha256', 'source_join'),
            ('retained_ALFRED_audit_sha256', 'policy_audit')):
        if review.get(field) != inputs[role]['sha256']:
            raise ValueError('source-use review link differs: ' + role)
    if review.get('source_audit_verified') is not False or review.get('research_admission_granted') is not False:
        raise ValueError('conditional source review cannot confer global certification or admission')
    joined = json.loads(snapshots['source_join'])
    hashes = {path.replace('\\', '/'): digest for path, digest in joined.get('fingerprints', {}).items()}
    for role in ('calendar', 'actions', *['bars_' + str(year) for year in range(2020, 2025)]):
        record = inputs[role]
        if hashes.get(record['path']) != record['sha256']:
            raise ValueError('price/action source join differs: ' + role)
    policy_hashes = review.get('newly_hash_checked_policy_files', {})
    if packet['source_origin'] == 'retained_research_sources':
        parser = 'src/quant_robot/data/alfred_monthly_vintages.py'
        if policy_hashes.get(parser) != packet['code_files'].get(parser):
            raise ValueError('executing policy parser differs from source-use review')
    for role in ('policy_1', 'policy_2'):
        record = inputs[role]
        if policy_hashes.get(record['path']) != record['sha256']:
            raise ValueError('policy source review differs: ' + role)
    scope = json.loads(snapshots['policy_scope'])
    if scope.get('observation_start') != '2018-01-01' or scope.get('observation_end') != '2024-05-01':
        raise ValueError('policy source window changed')


def _calendar(content):
    frame = pd.read_csv(io.BytesIO(content), dtype=str)
    if not {'market', 'date', 'is_open'}.issubset(frame.columns):
        raise ValueError('calendar fields missing')
    frame = frame[frame['market'].eq('CN')].copy()
    if not frame['date'].str.fullmatch(r'\d{4}-\d{2}-\d{2}').all():
        raise ValueError('calendar dates must be explicit dates')
    frame['date'] = frame['date'].map(date.fromisoformat)
    frame = frame[frame['date'].between(date(2020, 1, 2), date(2024, 6, 28))]
    if frame['date'].duplicated().any() or not set(frame['is_open']).issubset({'0', '1'}):
        raise ValueError('calendar duplicates or invalid open markers')
    sessions = sorted(frame.loc[frame['is_open'].eq('1'), 'date'])
    anchors = []
    for session in sessions:
        if not anchors or (session.year, session.month) != (anchors[-1].year, anchors[-1].month):
            anchors.append(session)
    months = [item.year * 12 + item.month for item in anchors]
    if months != list(range(2020 * 12 + 1, 2024 * 12 + 7)):
        raise ValueError('the original54monthly anchors must be complete')
    return [session for session in sessions if session <= anchors[-1]], anchors


def _signals(packet, snapshots, anchors):
    audit = json.loads(snapshots['policy_audit'])
    coverage = audit.get('coverage', [])
    expected = [(anchor.isoformat(), (anchor - timedelta(days=7)).isoformat()) for anchor in anchors]
    if audit.get('anchors_with_required_13_months') != 54 or [
            (row.get('execution_date'), row.get('vintage_date')) for row in coverage] != expected:
        raise ValueError('policy audit must bind the original54C-7cutoffs')
    batches = audit.get('batches', [])
    if len(batches) != 2 or [batch.get('index') for batch in batches] != [1, 2]:
        raise ValueError('exactly the two original policy batches required')
    if [v for batch in batches for v in batch.get('requested_vintages', [])] != [v for _, v in expected]:
        raise ValueError('policy batch vintage identities changed')
    panels, exact = [], {}
    for batch in batches:
        role = 'policy_' + str(batch['index'])
        if batch.get('csv_sha256') != packet['inputs'][role]['sha256']:
            raise ValueError('policy batch identity differs from audit')
        content = snapshots[role]
        panels.append(parse_alfred_monthly_vintages(content, series_id=SERIES,
            vintage_dates=batch['requested_vintages'], observation_start='2018-01-01', observation_end='2024-05-01'))
        # Preserve the original decimal token for median ties, after the existing
        # parser has checked columns, dates, duplicates, missingness and finiteness.
        for row in csv.DictReader(io.StringIO(content.decode('utf-8-sig'))):
            month = date.fromisoformat(row['observation_date'])
            for vintage in batch['requested_vintages']:
                exact[(vintage, month)] = row[SERIES + '_' + vintage.replace('-', '')]
    panel = pd.concat(panels, ignore_index=True)
    signals, details = [], []
    for index, ((anchor, vintage), row) in enumerate(zip(expected, coverage)):
        visible = panel[panel['vintage_date'].eq(pd.Timestamp(vintage)) & panel['value'].notna()]
        if visible.empty:
            raise ValueError('policy vintage is empty')
        latest = visible['observation_date'].max().date()
        if row.get('latest_available_observation') != latest.isoformat() or row.get('latest_month_and_prior_12_complete') is not True:
            raise ValueError('policy availability differs from frozen audit')
        months = [item.date() for item in pd.date_range(end=latest, periods=13, freq='MS')]
        values = {month: exact.get((vintage, month), '') for month in months}
        if any(value == '' for value in values.values()):
            raise ValueError('incomplete13-month policy input; no dropping or imputation')
        if index < 53:
            signals.append(monthly_median_gate(values))
            details.append({'anchor': anchor, 'vintage_date': vintage, 'latest_observation_month': latest.isoformat()})
    return signals, details


def calculate_from_snapshots(packet, snapshots):
    """Caller must have persisted the exclusive claim before entering here."""
    sessions, anchors = _calendar(snapshots['calendar'])
    signals, details = _signals(packet, snapshots, anchors)
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
    with tempfile.TemporaryDirectory(prefix='monthly-diagnostic-') as temporary:
        path = Path(temporary) / 'verified-actions.json'
        path.write_bytes(snapshots['actions'])
        prices = build_cash_action_research_prices(bars, path, sessions=sessions)
    if prices.evidence['cash_amount_basis'] not in {'gross', 'no_cash_events'}:
        raise ValueError('the fixed diagnostic requires gross cash source observations')
    indexed = prices.bars.set_index('date')['adj_close']
    levels = [indexed.loc[anchor] for anchor in anchors]
    diagnostic = monthly_selection_diagnostic(anchors, signals, levels)
    intervals = [{**detail, 'end_anchor': anchors[index + 1].isoformat(), 'signal': signals[index],
        'analytical_gross_return': str(Decimal(str(levels[index + 1])) / Decimal(str(levels[index])) - 1)}
        for index, detail in enumerate(details)]
    return {'stage': packet['stage'], 'registration_id': packet['registration_id'],
        'economic_hypothesis_id': packet['economic_hypothesis_id'], 'source_origin': packet['source_origin'],
        'diagnostic': diagnostic, 'intervals': intervals, 'analytical_price_evidence': prices.evidence,
        'conditional_assumption': 'no_unlisted_unit_conversion_in_the_bounded_window_not_proven',
        'net_account_result': False, 'qualifies_for_promotion': False,
        'counts_as_forward_paper_days': 0, 'formal_positive_ev_verified': False,
        'signal_ones': sum(signals), 'signal_zeros': len(signals) - sum(signals)}
