"""Finite, nonoverlapping event holdings in an offline conditional cash account.

Orders are hypothetical close fills. Entry quantities use the prior close; risk
observed at a close can only affect subsequent sessions. This grants no research
admission, price-source certification or live execution capability.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import math
from pathlib import Path

from quant_robot.paper.account_comparison import calendar_date
from quant_robot.paper.corporate_actions import CorporateActionLedger
from quant_robot.paper.fixed_hold import FixedHoldConfig, FixedHoldEntry, _validate
from quant_robot.paper.simulator import (
    _affordable_quantity, _apply_fills, _current_prices_by_date, _equity_row,
    _fill_price, _latest_prices_by_date, _positions_frame, _sanitize, _simulate_fills,
)
from quant_robot.backtest.costs import trade_commission
from quant_robot.research.announced_cash_ledger import AnnouncedCashResearchLedger
from quant_robot.storage.input_provenance import describe_input_frame


@dataclass(frozen=True)
class ScheduledEntry:
    event_id: str
    known_by: date
    entry_date: date


@dataclass(frozen=True)
class EventHoldConfig:
    asset_id: str
    corporate_actions_path: Path
    hold_transitions: int = 20
    initial_cash: float = 10000
    commission_bps: float = 5
    minimum_commission: float = 5
    slippage_bps: float = 5
    market_impact_bps: float = 2
    max_participation_rate: float = .01
    max_position_cny: float = 1000
    max_daily_loss_cny: float = 60
    max_drawdown: float = .08
    cash_amount_policy: str = 'net_only'


def run_event_hold_account(bars, config: EventHoldConfig, *, entries, sessions) -> dict:
    calendar, frame, schedule = _inputs(bars, config, entries, sessions)
    prices = _current_prices_by_date(frame, calendar)
    marks = _latest_prices_by_date(frame, calendar)
    positions, cash = {}, float(config.initial_cash)
    ledger_type = (CorporateActionLedger if config.cash_amount_policy == 'net_only'
                   else AnnouncedCashResearchLedger)
    actions = ledger_type(config.corporate_actions_path, {config.asset_id}, calendar, positions)
    rows, fills, events, breaches, cycles = [], [], [], [], []
    peak, previous_equity = cash, cash
    active, pending_exit, halted = None, None, False
    for index, session in enumerate(calendar):
        occupied_at_start = bool(positions)
        outgoing = []
        if active and (pending_exit or index >= active['exit_index']):
            reason = pending_exit or 'scheduled_exit'
            outgoing = [_intent(active['event_id'], config.asset_id, calendar[index - 1], session,
                                -positions[config.asset_id], reason,
                                float(prices[calendar[index - 1]].iloc[0]['latest_price']))]
            pending_exit = reason
        received, outgoing = actions.before_session(session, positions, outgoing)
        cash += received
        if pending_exit and occupied_at_start:
            proposed, rejected = _fills(outgoing, prices[session], config, cash)
            events.extend(rejected)
            for fill in proposed:
                fill['exit_reason'] = pending_exit
            cash = _apply_fills(positions, cash, proposed)
            fills.extend(proposed)
            if not positions:
                cycles.append({**active, 'exit_date': str(session), 'exit_reason': pending_exit})
                active, pending_exit = None, None
        if index in schedule:
            entry = schedule[index]
            reason = ('risk_halted' if halted else 'overlapping_or_exit_day' if occupied_at_start
                      else 'share_conversion_entry_day' if any(event['kind'] == 'share_split'
                          and event['ex_date'] == session for event in actions.events) else None)
            if reason:
                events.append({'event_id': entry.event_id, 'execution_date': str(session), 'reason': reason})
            else:
                new_fills, rejected = _enter(entry, index, calendar, prices, marks, config, cash, actions.receivable)
                events.extend(rejected)
                cash = _apply_fills(positions, cash, new_fills)
                fills.extend(new_fills)
                if new_fills:
                    active = {'event_id': entry.event_id, 'entry_date': str(session),
                              'entry_index': index, 'exit_index': index + config.hold_transitions}
        cash_before_close = cash
        cash += actions.after_session(session, positions)
        row = {**_equity_row(session, cash, positions, marks[session], actions.receivable),
               'cash_before_close': cash_before_close}
        if any(not math.isfinite(row[key]) for key in ('cash', 'equity', 'dividend_receivable')) or row['equity'] <= 0:
            raise ValueError('Account values must stay finite with positive equity')
        peak = max(peak, row['equity'])
        day_breaches = _risk_breaches(row, previous_equity, peak, config)
        breaches.extend(day_breaches)
        if day_breaches:
            halted = True
            if positions:
                pending_exit = 'risk_exit'
        rows.append(row)
        previous_equity = row['equity']
    request = {**asdict(config), 'corporate_actions_path': str(config.corporate_actions_path),
        'entries': [asdict(schedule[index]) for index in sorted(schedule)],
        'sessions': [str(d) for d in calendar], 'cash_annual_return': 0,
        'entry_policy': 'prior_close_lots_once_next_session_close_subject_to_current_cap_and_constraints',
        'exit_policy': 'entry_index_plus_hold_transitions_close_retry_until_flat',
        'risk_policy': 'permanent_entry_halt_next_session_close_exit_with_daily_retry',
        'commission_rounding': 'commission_and_impact_separately_half_up_0.01_assumption',
        'fill_price_tick_verified': False}
    equity = [config.initial_cash, *(row['equity'] for row in rows)]
    running_peak, max_drawdown = equity[0], 0.0
    for value in equity:
        running_peak = max(running_peak, value)
        max_drawdown = max(max_drawdown, 1 - value / running_peak)
    return _sanitize({'artifact_type': 'event_hold_conditional_cash_account_v1', 'request': request,
        'data_mode': 'fixture' if set(frame['source']) == {'fixture'} else 'research',
        'executable': False, 'research_admission_verified': False, 'net_positive_ev_verified': False,
        'input_provenance': {'bars': describe_input_frame(frame, role='event_hold_raw_history'),
            'source_quality_verified': False, 'fills_are_hypothetical': True,
            'execution_flag_columns_present': sorted(set(frame.columns) & {'suspended', 'limit_up', 'limit_down'}),
            'quote_depth_and_flag_completeness_verified': False}, 'accounting': actions.evidence(),
        'metrics': {'initial_equity': config.initial_cash, 'ending_equity': rows[-1]['equity'],
            'ending_cash': cash, 'pnl_cny': rows[-1]['equity'] - config.initial_cash,
            'total_return': rows[-1]['equity'] / config.initial_cash - 1,
            'max_drawdown': max_drawdown, 'fees_paid': sum(fill['fee'] for fill in fills),
            'fill_count': len(fills), 'completed_round_trips': len(cycles),
            'ending_dividend_receivable': actions.receivable,
            'dividend_cash_received': actions.dividend_cash_received},
        'risk': {'new_entries_halted': halted, 'breaches': breaches,
            'terminal_settled': not positions and actions.receivable == 0,
            'limits_are_triggers_not_guaranteed_loss_caps': True,
            'full_execution_admission_verified': False},
        'equity_curve': rows, 'fills': fills, 'positions': _positions_frame(positions).to_dict(orient='records'),
        'cycles': cycles, 'execution_events': events, 'corporate_action_events': actions.journal})


def _inputs(bars, config, entries, sessions):
    if not isinstance(config, EventHoldConfig) or type(config.hold_transitions) is not int or config.hold_transitions < 1:
        raise ValueError('Positive integer hold transitions required')
    if config.cash_amount_policy not in ('net_only', 'gross_announcement_assumption'):
        raise ValueError('Explicit supported cash amount policy required')
    # Reuse the dense raw-bar/calendar and monetary validation without running a benchmark.
    fixed = FixedHoldConfig(entries=(FixedHoldEntry(config.asset_id, 100, config.max_position_cny / 100),),
        **{key: getattr(config, key) for key in FixedHoldConfig.__dataclass_fields__ if key != 'entries'})
    calendar, frame = _validate(bars, fixed, sessions)
    schedule, seen = {}, set()
    for entry in entries:
        if not isinstance(entry, ScheduledEntry) or not isinstance(entry.event_id, str) or not entry.event_id.strip():
            raise ValueError('Explicit named entry required')
        known, session = calendar_date(entry.known_by), calendar_date(entry.entry_date)
        if entry.event_id in seen or session not in calendar:
            raise ValueError('Entry identity or session missing/duplicated')
        index = calendar.index(session)
        if index in schedule or index == 0 or not calendar[index - 1] <= known < session:
            raise ValueError('Entry must be the first explicit session strictly after known-by date')
        if index + config.hold_transitions >= len(calendar):
            raise ValueError('Entry requires a complete scheduled exit horizon')
        seen.add(entry.event_id)
        schedule[index] = entry
    return calendar, frame, schedule


def _intent(event_id, asset, signal_date, execution_date, quantity, reason, reference_price):
    return {'intent_id': f'{event_id}:{reason}:{execution_date}', 'asset_id': asset, 'market': 'CN_ETF',
        'signal_date': str(signal_date), 'execution_date': str(execution_date),
        'side': 'buy' if quantity > 0 else 'sell', 'signed_quantity': quantity,
        'intended_quantity': abs(quantity), 'reference_price': reference_price}


def _fills(intents, prices, config, cash):
    proposed, events = _simulate_fills(intents, prices, config.commission_bps, config.slippage_bps,
        config.market_impact_bps, config.max_participation_rate, cash,
        respect_execution_constraints=True, minimum_commission=config.minimum_commission)
    if not proposed:
        return proposed, events
    if len(proposed) != 1:
        raise ValueError('Event account supports a single order per session')
    fill = proposed[0]
    for field in ('commission_fee', 'market_impact_fee'):
        fill[field] = float(Decimal(str(fill[field])).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
    fill['fee'] = fill['commission_fee'] + fill['market_impact_fee']
    if fill['signed_quantity'] > 0 and fill['notional'] + fill['fee'] > cash + 1e-9:
        # The common fill engine uses unrounded fees. One fewer whole lot is the
        # deterministic correction when the explicit cent rule exceeds cash.
        quantity = fill['quantity'] - 100
        if quantity > 0:
            return _fills([{**intents[0], 'signed_quantity': quantity, 'intended_quantity': quantity}],
                          prices, config, cash)
        return [], [{'reason': 'cash_below_one_lot_after_fee_rounding', 'intent_id': fill['intent_id']}]
    if fill['signed_quantity'] < 0 and fill['fee'] > cash + fill['notional']:
        return [], [{'reason': 'insufficient_sale_proceeds_after_fee_rounding', 'intent_id': fill['intent_id']}]
    return proposed, events


def _enter(entry, index, calendar, prices, marks, config, cash, receivable):
    prior = float(prices[calendar[index - 1]].iloc[0]['latest_price'])
    unit_cost = _fill_price(prior, 1, config.slippage_bps)
    quantity = math.floor(config.max_position_cny / unit_cost / 100) * 100
    quantity = _affordable_quantity(quantity, 100, cash,
        lambda q: q * unit_cost + trade_commission(q * unit_cost, config.commission_bps, config.minimum_commission))
    session = calendar[index]
    base = {'event_id': entry.event_id, 'execution_date': str(session)}
    if quantity <= 0:
        return [], [{**base, 'reason': 'entry_below_one_lot_with_fees'}]
    fill_price = _fill_price(float(prices[session].iloc[0]['latest_price']), 1, config.slippage_bps)
    if quantity * fill_price > config.max_position_cny + 1e-9:
        return [], [{**base, 'reason': 'entry_position_limit'}]
    intent = _intent(entry.event_id, config.asset_id, calendar[index - 1], session, quantity, 'entry', prior)
    proposed, rejected = _fills([intent], prices[session], config, cash)
    if not proposed:
        return [], rejected or [{**base, 'reason': 'entry_unfilled'}]
    test_positions = {}
    test_cash = _apply_fills(test_positions, cash, proposed)
    equity = _equity_row(session, test_cash, test_positions, marks[session], receivable)['equity']
    if cash + receivable - equity >= config.max_daily_loss_cny:
        return [], [{**base, 'reason': 'entry_daily_loss_limit'}]
    return proposed, rejected


def _risk_breaches(row, previous_equity, peak, config):
    reasons = []
    if previous_equity - row['equity'] >= config.max_daily_loss_cny:
        reasons.append('daily_loss_limit')
    if 1 - row['equity'] / peak >= config.max_drawdown:
        reasons.append('drawdown_limit')
    if any(value['market_value'] > config.max_position_cny + 1e-9 for value in row['position_values'].values()):
        reasons.append('position_limit')
    return [{'date': str(row['date']), 'reason': reason, 'equity': row['equity']} for reason in reasons]
