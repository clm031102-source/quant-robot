"""Explicit cash-action research prices, separate from an executable cash account.

The index reinvests declared per-share cash at the ex-date close, with fractional
units and no trading costs. It neither reproduces every provider's adjustment
factor nor proves when the source information was actually available.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from quant_robot.paper.corporate_actions import validate_corporate_action_dataset
from quant_robot.storage.fingerprints import fingerprint_frame


PRICE_BASIS = 'cash_actions_ex_close_reinvestment_v1'


@dataclass(frozen=True)
class ResearchPriceBasisResult:
    bars: pd.DataFrame
    observations: pd.DataFrame
    evidence: dict[str, Any]


def build_cash_action_research_prices(
    bars: pd.DataFrame,
    actions_path: str | Path,
    *,
    sessions: Iterable[date],
) -> ResearchPriceBasisResult:
    """Build forward-linked research prices from a dense, explicitly dated panel.

    Raw OHLC fields are preserved. Only ``adj_close`` is replaced, with a named
    analytical basis. ``adjusted=True`` means this transformation was performed,
    not that source history, PIT availability or research admission is verified.
    The caller must separately qualify the raw price and action sources.
    """
    calendar = [_session(value) for value in sessions]
    if not calendar or calendar != sorted(set(calendar)):
        raise ValueError('Research price calendar must be nonempty, unique and increasing')
    required = {'date', 'asset_id', 'market', 'currency', 'close'}
    if bars.empty or not required.issubset(bars.columns):
        raise ValueError('Research prices require nonempty bars with date, asset_id, market, currency and raw close')
    if set(bars['market']) != {'CN_ETF'} or set(bars['currency']) != {'CNY'}:
        raise ValueError('This research price basis requires CN_ETF prices and distributions in CNY')
    if not bars['asset_id'].map(lambda value: isinstance(value, str) and bool(value.strip())).all():
        raise ValueError('Research price asset identities must be explicit')
    frame = bars.copy(deep=True)
    input_fingerprint = fingerprint_frame(frame)
    frame['date'] = frame['date'].map(_session)
    frame = frame.sort_values(['asset_id', 'date']).reset_index(drop=True)
    if frame.duplicated(['asset_id', 'date']).any():
        raise ValueError('Duplicate asset dates in research prices')
    for _, group in frame.groupby('asset_id', sort=False):
        if group['date'].tolist() != calendar:
            raise ValueError('Every research asset must match the explicit session calendar without gaps')
    closes = [_positive_decimal(value, 'raw close') for value in frame['close']]

    raw_actions = Path(actions_path).read_bytes()
    dataset = json.loads(raw_actions, parse_float=Decimal)
    events = validate_corporate_action_dataset(dataset, set(frame['asset_id']), calendar)
    exact_events = {item['event_id']: item for item in dataset['events']}
    by_date = _events_by_date(events, exact_events, calendar)
    records: list[dict[str, Any]] = []
    levels: list[float] = []
    for asset, group in frame.groupby('asset_id', sort=False):
        previous: Decimal | None = None
        level = Decimal(0)
        for index, row in group.iterrows():
            close = closes[index]
            event = by_date.get((asset, row['date']))
            cash, ratio = Decimal(0), Decimal(1)
            if event:
                if event['kind'] == 'cash_dividend':
                    cash = _positive_decimal(event['net_cash_per_share'], 'declared cash per share')
                else:
                    ratio = _positive_decimal(event['share_ratio'], 'share ratio')
            with localcontext() as context:
                context.prec = 34
                if previous is None:
                    # The initial close is the reference state; no pre-window right is invented.
                    level, step = close, None
                else:
                    step = (close * ratio + cash) / previous - 1
                    level *= 1 + step
                numeric_level = float(level)
                if not math.isfinite(numeric_level) or numeric_level <= 0:
                    raise ValueError('Research price index cannot be represented as a finite positive value')
                if step is not None and not math.isfinite(float(step)):
                    raise ValueError('Research price daily change cannot be represented as a finite value')
                levels.append(numeric_level)
                records.append({'date': row['date'], 'asset_id': asset, 'raw_close': float(close),
                    'declared_cash_per_share': str(cash), 'share_ratio': str(ratio),
                    'event_id': event['event_id'] if event else None,
                    'step_return': float(step) if step is not None else None,
                    'research_price': numeric_level})
            previous = close
    frame['adj_close'] = levels
    frame['adjusted'] = True
    frame['research_price_basis'] = PRICE_BASIS
    observations = pd.DataFrame(records)
    evidence = {
        'price_basis': PRICE_BASIS,
        'formula': 'index_t = index_prev * (raw_close_t * share_ratio_t + declared_cash_t) / raw_close_prev',
        'initial_level': 'first_raw_close_per_asset',
        'reinvestment': 'theoretical_fractional_units_at_ex_date_close',
        'cash_amount_basis': 'declared_net_cash_per_share_without_independent_tax_verification',
        'holder_rounding': 'not_applied_to_theoretical_index',
        'first_date': str(calendar[0]), 'last_date': str(calendar[-1]),
        'sessions': len(calendar), 'asset_count': frame['asset_id'].nunique(),
        'source_ref': dataset['source_ref'],
        'action_file_sha256': hashlib.sha256(raw_actions).hexdigest(),
        'input_bars_sha256': input_fingerprint,
        'output_bars_sha256': fingerprint_frame(frame),
        'calendar_sha256': hashlib.sha256(json.dumps([str(value) for value in calendar]).encode()).hexdigest(),
        'applied_events': len(by_date),
        'source_audit_verified': False,
        'research_admission_verified': False,
        'account_cash_or_tradability_verified': False,
        'source_revision_and_known_at_verified': False,
        'transaction_costs_included': False,
    }
    return ResearchPriceBasisResult(frame, observations, evidence)


def _events_by_date(events: list[dict[str, Any]], exact: dict[str, dict[str, Any]],
                    calendar: list[date]) -> dict[tuple[str, date], dict[str, Any]]:
    result: dict[tuple[str, date], dict[str, Any]] = {}
    positions = {session: index for index, session in enumerate(calendar)}
    for event in events:
        ex_date = event['ex_date']
        if not calendar[0] < ex_date <= calendar[-1]:
            continue
        if ex_date not in positions:
            raise ValueError('An action ex-date is missing from the research calendar')
        if event['kind'] == 'cash_dividend' and event['record_date'] != calendar[positions[ex_date] - 1]:
            raise ValueError('Research cash dividend requires the immediately preceding session as record date')
        key = (event['asset_id'], ex_date)
        if key in result:
            raise ValueError('Same-day cash dividend and share conversion require an explicit per-share unit rule')
        result[key] = exact[event['event_id']]
    return result


def _positive_decimal(value: Any, name: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f'{name} must be finite and positive') from exc
    if not number.is_finite() or number <= 0 or not math.isfinite(float(number)) or float(number) <= 0:
        raise ValueError(f'{name} must be finite and positive')
    return number


def _session(value: Any) -> date:
    if not isinstance(value, (str, date, pd.Timestamp)):
        raise ValueError('Research price dates must be explicit calendar dates')
    try:
        parsed = pd.Timestamp(value)
    except (ValueError, TypeError) as exc:
        raise ValueError('Invalid research price calendar date') from exc
    if pd.isna(parsed) or parsed.tzinfo is not None or parsed != parsed.normalize():
        raise ValueError('Research price dates must be timezone-free calendar dates')
    return parsed.date()
