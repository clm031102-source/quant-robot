"""Decode the calendar study's separately verified snapshots after its claim."""
from datetime import date
import io
import json
from pathlib import Path
import tempfile

import pandas as pd

from quant_robot.data.cn_calendar_snapshot import calendar_rows_from_snapshot
from quant_robot.research.month_start_liquidity_diagnostic import HYPOTHESIS, month_start_diagnostic
from quant_robot.research.price_basis import build_cash_action_research_prices

PROPOSAL_SHA256 = 'c1a7a077d5b9bd7ecc4a765f23c37f8f328c1ffb9c8f9d1a90e6ea06fab34161'
ASSET = 'CN_ETF_XSHG_510300'
PRICE_ROLES = ('calendar', 'calendar_manifest', 'actions', *['bars_'+str(y) for y in range(2020, 2025)])


def reviewed_calendar(snapshots):
    rows = calendar_rows_from_snapshot(snapshots['calendar'], snapshots['calendar_manifest'],
        start=date(2020, 1, 1), end=date(2024, 6, 3))
    sessions = [day for day, opened in rows if opened]
    if (len(rows) != 1616 or len(sessions) != 1069
            or sessions[0] != date(2020, 1, 2) or sessions[-1] != date(2024, 6, 3)):
        raise ValueError('fixed calendar coverage differs from the reviewed source')
    return rows, sessions


def check_source_links(packet, snapshots):
    """Check bound evidence and calendar only, without computing positions/prices."""
    try:
        inputs = packet['inputs']
        proposal = json.loads(snapshots['proposal'])
        if (packet['source_origin'] == 'retained_research_sources'
                and inputs['proposal']['sha256'] != PROPOSAL_SHA256):
            raise ValueError('real inputs require the frozen month-start proposal')
        if proposal.get('economic_hypothesis_id') != HYPOTHESIS:
            raise ValueError('proposal economic identity differs')
        review = json.loads(snapshots['source_review'])
        if (review.get('status') != 'conditional_calendar_source_use_reviewed_not_execution_admission'
                or review.get('economic_hypothesis_id') != HYPOTHESIS):
            raise ValueError('specific conditional source-use review required')
        for field in ('historical_version_assumption_verified', 'source_audit_verified',
                      'research_admission_granted', 'factor_or_return_computed', 'real_calendar_positions_generated'):
            if review.get(field) is not False:
                raise ValueError('source-use review cannot confer outcome or execution permission')
        if (review.get('proposal_sha256') != inputs['proposal']['sha256']
                or review.get('retained_source_join_sha256') != inputs['source_join']['sha256']
                or review.get('inputs') != {r: v for r, v in inputs.items() if r != 'source_review'}):
            raise ValueError('reviewed proposal or input identities differ')
        joined = json.loads(snapshots['source_join'])
        hashes = {path.replace('\\', '/'): digest for path, digest in joined.get('fingerprints', {}).items()}
        verified = {path.replace('\\', '/'): digest
                    for path, digest in review.get('verified_component_fingerprints', {}).items()}
        if hashes != verified or len(hashes) != review.get('verified_component_file_count'):
            raise ValueError('component review does not bind the source join')
        if packet['source_origin'] == 'retained_research_sources' and len(hashes) != 29:
            raise ValueError('all 29 reviewed source components required')
        for role in PRICE_ROLES:
            if hashes.get(inputs[role]['path']) != inputs[role]['sha256']:
                raise ValueError('price/action/calendar component identity differs: '+role)
        if (review.get('complete_civil_day_rows') != 1616 or review.get('open_session_count') != 1069
                or review.get('derived_closed_day_count') != 547):
            raise ValueError('calendar representation review differs')
        reviewed_calendar(snapshots)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('source review fields missing or malformed') from exc


def calculate_from_snapshots(packet, snapshots):
    """Caller must durably claim this study before decoding real outcome fields."""
    calendar, sessions = reviewed_calendar(snapshots)
    frames = []
    for year in range(2020, 2025):
        frame = pd.read_parquet(io.BytesIO(snapshots['bars_'+str(year)]), engine='pyarrow',
            columns=['date', 'asset_id', 'market', 'currency', 'close'],
            filters=[('asset_id', '==', ASSET), ('date', '>=', pd.Timestamp(sessions[0])),
                     ('date', '<=', pd.Timestamp(sessions[-1]))])
        if not frame.empty and not pd.to_datetime(frame['date']).dt.year.eq(year).all():
            raise ValueError('bar content does not match its fixed year')
        frames.append(frame)
    bars = pd.concat(frames, ignore_index=True)
    with tempfile.TemporaryDirectory(prefix='month-start-diagnostic-') as temporary:
        actions = Path(temporary)/'actions.json'; actions.write_bytes(snapshots['actions'])
        prices = build_cash_action_research_prices(bars, actions, sessions=sessions)
    if prices.evidence['cash_amount_basis'] not in {'gross', 'no_cash_events'}:
        raise ValueError('diagnostic requires reviewed gross cash observations')
    indexed = prices.bars.set_index('date')['adj_close']
    diagnostic = month_start_diagnostic(calendar, {day: indexed.loc[day] for day in sessions},
        first_month=date(2020, 1, 1), last_month=date(2024, 5, 1))
    if (diagnostic['cycle_count'] != 53 or diagnostic['selected_close_to_close_transitions'] != 106
            or diagnostic['gross_diagnostic']['total_close_to_close_transitions'] != 1068):
        raise ValueError('fixed study dimensions differ; no alternate scope permitted')
    return {'stage': packet['stage'], 'registration_id': packet['registration_id'],
        'economic_hypothesis_id': HYPOTHESIS, 'source_origin': packet['source_origin'],
        'diagnostic': diagnostic, 'analytical_price_evidence': prices.evidence,
        'historical_version_assumption_verified': False, 'source_audit_verified': False,
        'net_account_result': False, 'qualifies_for_promotion': False,
        'counts_as_forward_paper_days': 0, 'formal_positive_ev_verified': False}
