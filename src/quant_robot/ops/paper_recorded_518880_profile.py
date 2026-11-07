"""One proposed identity, with no production source registration or guessed parser.

The retained 2024 annual report is not current identity/tradability/coverage.
Daily originals belong in scoped proofs, never in the profile's code identity.
"""
from types import MappingProxyType

ASSET_ID = 'CN_ETF_XSHG_518880'
TS_CODE = '518880.SH'
PROFILE_ID = 'recorded_xshg_518880_v1'
OFFLINE_PROFILE_ID = 'synthetic_recorded_connection_518880_v1'
RECORDED_PROFILES = MappingProxyType({})
MISSING = ('reviewed_current_identity_and_provenance',
           'reviewed_daily_execution_parser_and_provenance',
           'reviewed_complete_action_parser_and_provenance',
           'reviewed_applicable_calendar_and_permitted_warmup')


def reviewed_profile_518880():
    """Deliberately unavailable until official facts and fixed formats are reviewed."""
    raise ValueError('recorded_518880_profile_unavailable:' + ','.join(MISSING))


def profile_binding(*, stage=None):
    # No input document or synthetic fixture can complete this missing admission.
    reviewed_profile_518880()


def readiness():
    return dict(profile_id=PROFILE_ID, asset_id=ASSET_ID, registered=False,
                missing=list(MISSING), production_admission=False,
                qualified_candidates_added=0, real_forward_days_added=0)
