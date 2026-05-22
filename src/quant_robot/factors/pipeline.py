from __future__ import annotations

import pandas as pd

from quant_robot.factors.technical import compute_basic_factors


def run_factor_pipeline(bars: pd.DataFrame, windows: tuple[int, ...] = (5, 20)) -> pd.DataFrame:
    return compute_basic_factors(bars, windows=windows)
