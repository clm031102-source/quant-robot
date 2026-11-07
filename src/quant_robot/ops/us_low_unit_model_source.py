"""Fixed low-unit basket source adapter, separate from journal admission.

One four-asset observation can feed four independent conditional accounts.
This adapter neither creates an account nor grants a source/research release.
Provider daily bars are not exchange execution evidence. Splits/capital gains
still block before numeric conversion until a separately reviewed action route
exists. No provider values are relabelled as artificial journal events.
"""
from decimal import Decimal

from quant_robot.ops import us_allocation_model_capture as capture
from quant_robot.ops import us_allocation_source_contract as source


ASSETS = ('SPYM', 'EFA', 'IEF', 'GLDM')
DAILY_FIELDS = ('open', 'high', 'low', 'close', 'volume')


def expected_url(symbol, start, end):
    return capture.expected_url(symbol, start, end, assets=ASSETS)


def describe(raw, reference, *, symbol):
    return source.describe_yahoo_source(raw, reference, symbol=symbol, assets=ASSETS)


def assess(packet, schedule, *, authorities):
    return source.assess_source_metadata(packet, schedule, authorities=authorities, assets=ASSETS)


def normalize(raw_by_symbol, packet, schedule, *, authorities, context, before_numeric_decode):
    """Convert one bound snapshot once; retain its original evidence identity.

    In this no-split window contract, quoted share volume also supplies nominal
    capacity volume. A split in the query blocks instead of silently adjusting
    earlier bars. Warmup dividends create no inherited receivables.
    """
    result = source.normalize_yahoo_sources(raw_by_symbol, packet, schedule,
        authorities=authorities, context=context, before_numeric_decode=before_numeric_decode,
        assets=ASSETS, daily_fields=DAILY_FIELDS, dividend_assets=ASSETS[:3])
    for day in result['days']:
        if result['purpose'] == 'daily_model':
            for row in day['prices'].values():
                low, high = Decimal(row['low']), Decimal(row['high'])
                if not low <= min(Decimal(row['open']), Decimal(row['close'])) <= max(
                        Decimal(row['open']), Decimal(row['close'])) <= high:
                    raise ValueError('daily_OHLC_order')
        day['capacity_volume'] = {symbol:day['prices'][symbol]['volume'] for symbol in ASSETS}
    result.update(schema='us_low_unit_source_normalized_packet_v1', assets=list(ASSETS),
        splits=[], capital_gains=[], model_accounts_advanced=0,
        capacity_basis='nominal_provider_volume_no_split_in_query',
        daily_fields=list(DAILY_FIELDS), journal_admission_granted=False)
    return result
