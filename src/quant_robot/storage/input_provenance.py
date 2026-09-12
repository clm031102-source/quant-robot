"""Describe actual in-memory calculation inputs without certifying their sources."""
from __future__ import annotations

import hashlib
import json
from typing import Any

import pandas as pd

from quant_robot.storage.fingerprints import fingerprint_frame, fingerprint_schema


def describe_input_frame(frame: pd.DataFrame, *, role: str) -> dict[str, Any]:
    """Record exact row order, schema and values under the current pandas version.

    The existing frame fingerprint deliberately ignores the index. This is a
    versioned calculation identity, not a file signature or a source-quality audit.
    """
    assets = sorted(frame['asset_id'].astype(str).unique()) if 'asset_id' in frame else []
    dates = pd.to_datetime(frame['date']).dt.date if 'date' in frame else pd.Series(dtype=object)
    return {
        'role': role,
        'fingerprint_algorithm': 'pandas_row_hash_schema_sha256_v1',
        'pandas_version': pd.__version__,
        'content_sha256': fingerprint_frame(frame),
        'schema_sha256': fingerprint_schema(frame),
        'schema': [{'column': str(column), 'dtype': str(frame[column].dtype)} for column in frame.columns],
        'row_count': len(frame),
        'asset_count': len(assets),
        'asset_set_sha256': hashlib.sha256(json.dumps(assets, separators=(',', ':')).encode()).hexdigest(),
        'markets': sorted(frame['market'].astype(str).unique()) if 'market' in frame else [],
        'source_labels': sorted(frame['source'].astype(str).unique()) if 'source' in frame else [],
        'first_date': str(dates.min()) if len(dates) else None,
        'last_date': str(dates.max()) if len(dates) else None,
    }


def describe_calculation_inputs(
    bars: pd.DataFrame, factors: pd.DataFrame, *, artifact_role: str, factor_role: str,
) -> dict[str, Any]:
    return {
        'schema_version': 1,
        'artifact_role': artifact_role,
        'scope': 'bar_and_factor_frame_identity_only',
        'bars': describe_input_frame(bars, role='filtered_bar_history_including_warmup'),
        'factors': describe_input_frame(factors, role=factor_role),
        'source_quality_verified': False,
        'research_admission_verified': False,
    }
