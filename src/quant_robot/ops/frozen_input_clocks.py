"""Explicit decision and observation clocks; this validates no source provenance."""
from datetime import datetime, timedelta


PROVIDER_BASIS = 'provider_generated_and_available_utc'
RECEIVED_BASIS = 'bound_originals_received_utc'
BASES = (PROVIDER_BASIS, RECEIVED_BASIS)


def instant(value):
    if not isinstance(value, str) or not value.endswith('Z') or 'T' not in value:
        raise ValueError('Explicit UTC timestamp ending in Z required')
    parsed = datetime.fromisoformat(value[:-1] + '+00:00')
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError('UTC required')
    return parsed


def session_clocks(session, basis):
    """Legacy fixtures retain their clocks; new receipts separate four events."""
    if basis == PROVIDER_BASIS:
        opening, closing = instant(session['open_at']), instant(session['close_at'])
        values = dict(cutoff=opening, opening=opening, closing=closing, observable=closing)
    elif basis == RECEIVED_BASIS:
        required = {'date', 'decision_cutoff_at', 'open_at', 'auction_close_at',
                    'daily_observation_not_before'}
        if set(session) != required:
            raise ValueError('Separate reviewed session clocks required')
        values = dict(zip(('cutoff', 'opening', 'closing', 'observable'),
            (instant(session[key]) for key in ('decision_cutoff_at', 'open_at',
             'auction_close_at', 'daily_observation_not_before')), strict=True))
        if any((value + timedelta(hours=8)).date().isoformat() != session['date']
               for value in values.values()):
            raise ValueError('Session clocks must match the China trading date')
    else:
        raise ValueError('Unsupported frozen source timestamp basis')
    if not values['cutoff'] <= values['opening'] < values['closing'] <= values['observable']:
        raise ValueError('Ordered nonoverlapping session clocks required')
    return values


def validate_schedule(schedule, basis):
    previous = None
    for session in schedule:
        label = datetime.strptime(session['date'], '%Y-%m-%d').date().isoformat()
        if label != session['date']:
            raise ValueError('ISO exchange session date required')
        clocks = session_clocks(session, basis)
        if previous is not None and clocks['cutoff'] <= previous:
            raise ValueError('Ordered nonoverlapping session clocks required')
        previous = clocks['observable']


def validate_input_clocks(packet, session, basis, *, now):
    """Validate causal timing without inventing provider publication timestamps.

    For observed originals, available_at is the latest bound evidence receipt;
    acquired_at is this journal's import time. External adapters must establish
    that binding: these fields alone never authorize real forward operation.
    """
    clocks = session_clocks(session, basis)
    available, acquired = (instant(packet[key]) for key in ('available_at', 'acquired_at'))
    if basis == PROVIDER_BASIS:
        generated = instant(packet['generated_at'])
        valid = clocks['observable'] <= generated <= available <= acquired <= now
    else:
        if ('generated_at' not in packet or packet['generated_at'] is not None
                or 'provider_first_publication_at' not in packet
                or packet['provider_first_publication_at'] is not None):
            raise ValueError('Unknown provider publication clocks must remain explicit null')
        requested, received = (instant(packet[key]) for key in
                               ('price_request_started_at', 'price_received_at'))
        # A request begun before the final observable session may cache a
        # partial daily response even if its last byte arrives afterwards.
        valid = clocks['observable'] <= requested <= received <= available <= acquired <= now
    if not valid:
        raise ValueError('Final-bar generation, availability and host receipt clocks are inconsistent')
    return clocks
