"""Explicit new B/P model preparation; only fabricated 2001 input is admitted.

This grants no permission to decode retained historical sources or resume an
old financial claim. Cash formula and event availability remain assumptions.
"""
from quant_robot.research.crypto_carry_model import CHARGE_BASIS_FUNDING
from quant_robot.research.crypto_monthly_diagnostic import (
    DAY, MARKETS, PRIMARY, START, RawMonthlyBundle, _assert_loaded,
    _decode_month_core, _run_account_core,
)


def load_charge_basis_fixture(raw: RawMonthlyBundle):
    """Reject actual-source/date inputs before any archive or financial decode."""
    if (not isinstance(raw,RawMonthlyBundle) or raw.evidence_class!='synthetic_raw_fixture'
            or raw.actual_market_acquired_at is not None or raw.historical_first_publication_at is not None):
        raise ValueError('historical_decode_requires_new_independent_admission_guard')
    days=(raw.end-raw.start).days
    if (raw.start!=START or not 2<=days<=31 or raw.end!=START+days*DAY
            or raw.fixture_created_at is None or raw.fixture_created_at.tzinfo is None
            or set(raw.archives)!=set(MARKETS)|{'funding'}):
        raise ValueError('fixed_fabricated_january_scope_required')
    return _decode_month_core(raw,funding_mode=CHARGE_BASIS_FUNDING)


def run_charge_basis_fixture(data, *, scenario=PRIMARY, output_dir):
    """One fixed synthetic cost scenario; no historical files or financial gate."""
    _assert_loaded(data)
    return _run_account_core(data,scenario=scenario,output_dir=output_dir,
                             funding_mode=CHARGE_BASIS_FUNDING)
