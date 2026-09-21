"""Offline intent signatures used to reject duplicate promotion candidates."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def paper_signal_signature(manifest_path: Any) -> set[str]:
    if not manifest_path:
        return set()
    path = Path(str(manifest_path))
    intents_path = path.with_name("intents.csv")
    if not intents_path.exists():
        return set()
    try:
        rows = pd.read_csv(intents_path)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return set()
    signature_columns = ["signal_date", "execution_date", "asset_id", "side"]
    if not set(signature_columns).issubset(rows.columns):
        return set()
    signature = set()
    for row in rows[signature_columns].itertuples(index=False):
        values = [str(value) for value in row]
        if all(value and value.lower() != "nan" for value in values):
            signature.add("|".join(values))
    return signature


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)
