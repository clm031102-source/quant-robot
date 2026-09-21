"""One fixed fiscal formula and account comparison over claimed byte snapshots."""
from datetime import date
import io
import json
from pathlib import Path
import tempfile

import pandas as pd

from quant_robot.data.cn_calendar_snapshot import calendar_rows_from_snapshot
from quant_robot.paper.event_hold import EventHoldConfig, ScheduledEntry, run_event_hold_account
from quant_robot.research.fiscal_execution_gate import HYPOTHESIS, evaluate_fiscal_gate
from quant_robot.research.fiscal_execution_decision import compare_fiscal_accounts
from quant_robot.research.fiscal_study_registration import REVIEW_PATH, PROPOSAL_PATH

ASSET = 'CN_ETF_XSHG_510300'
CALENDAR = 'data/processed/trading_calendars/cn_tushare_2015_2025/cn_trading_calendar.csv'
CALENDAR_MANIFEST = 'data/processed/trading_calendars/cn_tushare_2015_2025/cn_trading_calendar_manifest.json'
ACTIONS = 'data/reports/etf_monetization_20260911/research_price_basis_20260913/notice_source_contract/510300_notice_gross_observations_v3.json'
BARS = 'data/processed/tushare_etf_wide_history_2023_2026/processed/bars/frequency=1d/market=CN_ETF/year={year}/part-00000.parquet'


def calculate_from_snapshots(packet, snapshots):
    """Execution wrapper must have exclusively claimed before calling this function."""
    review, proposal = json.loads(snapshots[REVIEW_PATH]), json.loads(snapshots[PROPOSAL_PATH])
    eligibility = json.loads(snapshots[review['eligibility_manifest_path']])
    calendar = calendar_rows_from_snapshot(snapshots[CALENDAR], snapshots[CALENDAR_MANIFEST],
        start=date(2020, 1, 1), end=date(2024, 6, 28))
    sessions = [day for day, opened in calendar if opened]
    if packet['source_origin'] == 'retained_research_sources' and (
            len(sessions) != 1087 or sessions[0] != date(2020, 1, 2) or sessions[-1] != date(2024, 6, 28)):
        raise ValueError('Frozen fiscal price calendar differs')
    if len(eligibility['rows']) != 48 or sum(row['source_and_calendar_eligible'] for row in eligibility['rows']) != 43:
        raise ValueError('Frozen fiscal source eligibility differs')
    selected, unconditional, observations = [], [], []
    for row in eligibility['rows']:
        if not row['source_and_calendar_eligible']:
            observations.append({'period': row['period'], 'status': 'excluded_before_factor', 'reasons': row['exclusions']})
            continue
        period = row['period']; year = int(period[:4]); month = period[5:]
        current = json.loads(snapshots[review['monthly_sources'][period]['observation_path']])['observation']
        prior = json.loads(snapshots[review['monthly_sources'][f'{year-1}-{month}']['observation_path']])['observation']
        result = evaluate_fiscal_gate(current=current, prior=prior,
            current_plan=review['annual_references'][str(year)], prior_plan=review['annual_references'][str(year-1)],
            decision_day=row['assumed_entry_day'])
        entry_day = date.fromisoformat(row['assumed_entry_day'])
        index = sessions.index(entry_day)
        if str(sessions[index+20]) != row['scheduled_exit_day']:
            raise ValueError('Frozen twenty-transition horizon differs')
        entry = ScheduledEntry(period, date.fromisoformat(current['published_date_label']), entry_day)
        unconditional.append(entry)
        if result['selected']:
            selected.append(entry)
        observations.append({'status': 'evaluated', **result})
    frames = []
    for year in range(2020, 2025):
        frame = pd.read_parquet(io.BytesIO(snapshots[BARS.format(year=year)]), engine='pyarrow',
            filters=[('asset_id', '==', ASSET), ('date', '>=', pd.Timestamp(sessions[0])),
                     ('date', '<=', pd.Timestamp(sessions[-1]))])
        if not frame.empty and not pd.to_datetime(frame['date']).dt.year.eq(year).all():
            raise ValueError('Bar partition year differs')
        frames.append(frame)
    bars = pd.concat(frames, ignore_index=True)
    accounts, settings = {}, proposal['account']
    with tempfile.TemporaryDirectory(prefix='fiscal-account-snapshot-') as temporary:
        action_path = Path(temporary)/'actions.json'; action_path.write_bytes(snapshots[ACTIONS])
        for minimum in settings['minimum_commission_scenarios_cny']:
            config = EventHoldConfig(asset_id=ASSET, corporate_actions_path=action_path,
                cash_amount_policy=settings['dividend_policy'], minimum_commission=minimum,
                **{key: settings[key] for key in ('initial_cash', 'hold_transitions', 'commission_bps',
                    'slippage_bps', 'market_impact_bps', 'max_participation_rate', 'max_position_cny',
                    'max_daily_loss_cny', 'max_drawdown')})
            left = run_event_hold_account(bars, config, entries=selected, sessions=sessions)
            right = run_event_hold_account(bars, config, entries=unconditional, sessions=sessions)
            comparison = compare_fiscal_accounts(left, right)
            for account in (left, right):
                account['request']['corporate_actions_path'] = ACTIONS
                account['input_preparation'] = 'corporate actions executed from verified byte snapshot in a temporary file'
                account['annual_pnl_cny'] = annual_contributions(account)
            accounts[str(minimum)] = {'selected': left, 'unconditional': right, 'comparison': comparison}
    return {'stage': packet['stage'], 'registration_id': packet['registration_id'],
        'source_origin': packet['source_origin'], 'economic_hypothesis_id': HYPOTHESIS,
        'observation_count': len(observations), 'eligible_periods': len(unconditional),
        'selected_signal_periods': len(selected), 'fiscal_observations': observations,
        'scenarios': accounts, 'primary_decision': accounts['5']['comparison'],
        'source_audit_verified': False, 'historical_availability_verified': False,
        'formal_positive_ev_verified': False, 'counts_as_forward_paper_days': 0,
        'qualifies_for_promotion': False, 'net_account_cash_verified': False}


def annual_contributions(account):
    previous = account['metrics']['initial_equity']
    values = {}
    for row in account['equity_curve']:
        year = str(row['date'])[:4]
        values[year] = values.get(year, 0) + row['equity'] - previous
        previous = row['equity']
    return values
