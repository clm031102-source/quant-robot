"""A fee-paying fixed-hold comparison, using the existing paper account engine.

Entries are declared in entry-date units and attempted only on the second
explicit session. Prices are simulated raw closes plus declared slippage, not
certified executable quotes. Remaining holdings are marked, not liquidated.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date
from numbers import Real
from pathlib import Path
from typing import Iterable

import pandas as pd

from quant_robot.data.quality import validate_market_data
from quant_robot.paper.account_comparison import calendar_date
from quant_robot.paper.corporate_actions import CorporateActionLedger
from quant_robot.paper.economics import VALUATION_MODEL, execution_economics_from_request
from quant_robot.paper.simulator import (
    _apply_fills, _current_prices_by_date, _equity_curve, _equity_row,
    _fill_price, _latest_prices_by_date, _positions_frame, _sanitize, _simulate_fills,
)
from quant_robot.storage.input_provenance import describe_input_frame


@dataclass(frozen=True)
class FixedHoldEntry:
    asset_id: str
    quantity: int
    limit_price: float


@dataclass(frozen=True)
class FixedHoldConfig:
    entries: tuple[FixedHoldEntry, ...]
    initial_cash: float
    commission_bps: float
    minimum_commission: float
    slippage_bps: float
    market_impact_bps: float
    max_participation_rate: float
    corporate_actions_path: Path
    max_position_cny: float = 1000
    max_daily_loss_cny: float = 60
    max_drawdown: float = .08


def run_fixed_hold_benchmark(bars: pd.DataFrame, config: FixedHoldConfig, *,
                             sessions: Iterable[date]) -> dict:
    """Start entirely in cash, attempt declared buys once, then value every day.

    The input order fixes allocation priority when cash cannot fund every lot.
    There is no factor, reinvestment, retry, rebalancing or assumed terminal sale.
    Risk breaches after entry are reported; they do not invent liquidation fills.
    This in-memory analytical API grants no source or market-research admission.
    """
    calendar, frame = _validate(bars, config, sessions)
    assets = {entry.asset_id for entry in config.entries}
    prices = _current_prices_by_date(frame, calendar)
    marks = _latest_prices_by_date(frame, calendar)
    positions, cash = {}, float(config.initial_cash)
    actions = CorporateActionLedger(config.corporate_actions_path, assets, calendar, positions)
    rows, fills, events, breaches = [], [], [], []
    peak = float(config.initial_cash)
    for index, session in enumerate(calendar):
        received, _ = actions.before_session(session, positions, [])
        cash += received
        if index == 1:
            cash, new_fills, new_events = _enter(config, calendar, prices[session], marks[session],
                                                positions, cash, actions.receivable)
            fills.extend(new_fills)
            events.extend(new_events)
        cash_before_close = cash
        cash += actions.after_session(session, positions)
        actions.require_post_action_prices(session, positions,
            marks[session].set_index('asset_id')['price_date'].to_dict())
        row = {**_equity_row(session, cash, positions, marks[session], actions.receivable),
               'cash_before_close': cash_before_close}
        if not all(math.isfinite(float(row[key])) for key in ('cash', 'equity', 'dividend_receivable')):
            raise ValueError('Fixed-hold account values must remain finite')
        if row['equity'] <= 0:
            raise ValueError('Fixed-hold account equity must remain positive')
        peak = max(peak, row['equity'])
        if rows and rows[-1]['equity'] - row['equity'] >= config.max_daily_loss_cny:
            breaches.append({'date': str(session), 'reason': 'daily_loss_limit'})
        if 1 - row['equity'] / peak >= config.max_drawdown:
            breaches.append({'date': str(session), 'reason': 'drawdown_limit'})
        lookup = marks[session].set_index('asset_id')['latest_price'].to_dict()
        for asset, quantity in positions.items():
            if quantity * lookup[asset] > config.max_position_cny + 1e-9:
                breaches.append({'date': str(session), 'asset_id': asset, 'reason': 'position_limit'})
        rows.append(row)
    curve = _equity_curve(rows)
    request = {**asdict(config), 'market': 'CN_ETF', 'currency': 'CNY',
        'corporate_actions_path': str(config.corporate_actions_path),
        'corporate_actions_fingerprint': actions.fingerprint, 'valuation_model': VALUATION_MODEL,
        'sessions': [str(value) for value in calendar], 'cash_annual_return': 0.0,
        'entry_rule': 'declared_order_once_at_second_session_close_subject_to_price_and_risk_limits',
        'quantity_basis': 'entry_date_post_action_units', 'terminal_rule': 'mark_open_positions_no_exit_fees'}
    request['execution_economics'] = execution_economics_from_request(request)
    ending = rows[-1]['equity']
    return _sanitize({'artifact_type': 'fixed_hold_cash_account_v1',
        'data_mode': 'fixture' if set(frame['source']) == {'fixture'} else 'research',
        'request': request, 'accounting': actions.evidence(), 'executable': False,
        'input_provenance': {'bars': describe_input_frame(frame, role='fixed_hold_raw_price_history'),
                             'source_quality_verified': False, 'research_admission_verified': False},
        'metrics': {'initial_equity': config.initial_cash, 'ending_equity': ending,
            'ending_cash': cash, 'total_return': ending / config.initial_cash - 1,
            'max_drawdown': float((curve.equity / curve.equity.cummax() - 1).min()),
            'fees_paid': sum(fill['fee'] for fill in fills), 'fill_count': len(fills),
            'ending_dividend_receivable': actions.receivable,
            'dividend_cash_received': actions.dividend_cash_received},
        'risk': {'compatible_with_declared_limits': not breaches, 'breaches': breaches,
                 'entry_fully_filled': len(fills) == len(config.entries) and all(
                     fill['quantity'] == entry.quantity for fill, entry in zip(fills, config.entries)),
                 'post_entry_policy': 'observe_and_report_without_hypothetical_liquidation',
                 'full_execution_admission_verified': False},
        'equity_curve': curve.to_dict(orient='records'), 'fills': fills,
        'positions': _positions_frame(positions).to_dict(orient='records'),
        'execution_events': events, 'corporate_action_events': actions.journal})


def _enter(config, calendar, prices, marks, positions, cash, receivable):
    fills, events = [], []
    lookup = prices.set_index('asset_id')['latest_price'].to_dict()
    for number, entry in enumerate(config.entries):
        intent = {'intent_id': f'fixed-hold-{number}', 'asset_id': entry.asset_id,
            'market': 'CN_ETF', 'signal_date': str(calendar[0]), 'execution_date': str(calendar[1]),
            'side': 'buy', 'signed_quantity': entry.quantity}
        base = {'intent_id': intent['intent_id'], 'asset_id': entry.asset_id,
                'execution_date': str(calendar[1])}
        fill_price = _fill_price(float(lookup[entry.asset_id]), entry.quantity, config.slippage_bps)
        if fill_price > entry.limit_price:
            events.append({**base, 'reason': 'entry_price_above_limit'})
            continue
        proposed, rejected = _simulate_fills([intent], prices, config.commission_bps,
            config.slippage_bps, config.market_impact_bps, config.max_participation_rate, cash,
            respect_execution_constraints=True, minimum_commission=config.minimum_commission)
        events.extend(rejected)
        if not proposed:
            if not rejected:
                events.append({**base, 'reason': 'cash_below_one_lot_with_fees'})
            continue
        candidate_positions = dict(positions)
        candidate_cash = _apply_fills(candidate_positions, cash, proposed)
        candidate_equity = _equity_row(calendar[1], candidate_cash, candidate_positions, marks, receivable)['equity']
        if config.initial_cash - candidate_equity >= config.max_daily_loss_cny:
            events.append({**base, 'reason': 'entry_daily_loss_limit'})
            continue
        cash = _apply_fills(positions, cash, proposed)
        fills.extend(proposed)
        if proposed[0]['quantity'] < entry.quantity:
            events.append({**base, 'reason': 'cash_limited_partial_entry',
                           'requested_quantity': entry.quantity, 'filled_quantity': proposed[0]['quantity']})
    return cash, fills, events


def _validate(bars, config, sessions):
    for field in ('initial_cash', 'max_position_cny', 'max_daily_loss_cny', 'max_drawdown', 'max_participation_rate'):
        _number(getattr(config, field), field, positive=True)
    for field in ('commission_bps', 'minimum_commission', 'slippage_bps', 'market_impact_bps'):
        _number(getattr(config, field), field)
    if config.max_drawdown >= 1 or config.max_participation_rate > 1 or config.slippage_bps >= 10000:
        raise ValueError('Invalid drawdown, participation or slippage range')
    if not config.entries or any(not isinstance(x, FixedHoldEntry) for x in config.entries):
        raise ValueError('Explicit fixed-hold entries are required')
    if len({entry.asset_id for entry in config.entries}) != len(config.entries):
        raise ValueError('Duplicate fixed-hold entry assets')
    for entry in config.entries:
        if not isinstance(entry.asset_id, str) or not entry.asset_id.startswith('CN_ETF_'):
            raise ValueError('Explicit CN_ETF identity required')
        if type(entry.quantity) is not int or entry.quantity <= 0 or entry.quantity % 100:
            raise ValueError('Fixed-hold entry quantity must be positive whole 100-share lots')
        _number(entry.limit_price, 'entry limit price', positive=True)
        if entry.quantity * entry.limit_price > config.max_position_cny:
            raise ValueError('Declared fixed-hold entry exceeds position limit')
    if config.corporate_actions_path is None:
        raise ValueError('An explicit corporate-action source declaration is required')
    calendar = [calendar_date(value) for value in sessions]
    if len(calendar) < 2 or calendar != sorted(set(calendar)):
        raise ValueError('Fixed-hold calendar requires at least two unique increasing sessions')
    if bars.empty or 'asset_id' not in bars or 'date' not in bars:
        raise ValueError('Nonempty bars with explicit identities and dates are required')
    assets = {entry.asset_id for entry in config.entries}
    frame = bars[bars['asset_id'].isin(assets)].copy(deep=True)
    if set(frame['asset_id']) != assets:
        raise ValueError('Fixed-hold asset is missing from bars')
    frame['date'] = frame['date'].map(calendar_date)
    frame = frame.sort_values(['asset_id', 'date']).reset_index(drop=True)
    if frame.duplicated(['asset_id', 'date']).any() or any(
            group['date'].tolist() != calendar for _, group in frame.groupby('asset_id')):
        raise ValueError('Every fixed-hold asset must match the complete explicit calendar')
    validate_market_data(frame)
    if set(frame['market']) != {'CN_ETF'} or set(frame['currency']) != {'CNY'} or set(frame['frequency']) != {'1d'}:
        raise ValueError('Fixed-hold comparison requires daily CN_ETF prices in CNY')
    for field in ('open', 'high', 'low', 'close', 'volume'):
        for value in frame[field]:
            _number(value, 'raw price/volume', positive=field != 'volume')
    return calendar, frame


def _number(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f'{name} must be a finite number')
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f'{name} must be a finite number') from exc
    if not math.isfinite(number) or number < 0 or (positive and number == 0):
        raise ValueError(f'{name} must be finite and {"positive" if positive else "nonnegative"}')
