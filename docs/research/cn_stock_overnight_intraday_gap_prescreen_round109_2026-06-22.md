# CN Stock Round109 Overnight-Intraday Gap Prescreen

Round109 rotated away from the Round108 hard-redundant trend/amount line and tested a public-reference OHLC structure family: overnight gap, open-to-close intraday return, and gap-fill behavior. This was a statistical prescreen only. It does not promote any factor to paper-ready or live use.

## Scope

- Machine/task context: `office_desktop`, CN stock `factor_validation`.
- Data window: 2015-01-05 to 2025-12-31 bars.
- Assets: 5,707.
- Bar rows: 10,785,537.
- Candidate factors: 10.
- Horizons: 5 and 20 trading days.
- Tests: 20.
- Final holdout: not included.
- Safety: research-to-review only; no broker connection, account read, order placement, or live trading.

## Public Reference Basis

- Alphalens-style IC, quantile, and turnover prescreen before any portfolio grid.
- Qlib-style fixed feature formulas and windows rather than ad hoc parameter search.
- Public/academic overnight versus intraday return decomposition as the economic hypothesis.

## Results

| Metric | Value |
|---|---:|
| Factor rows | 101,307,965 |
| Label rows | 21,417,227 |
| Aligned rows | 201,128,582 |
| FDR-significant tests | 13 |
| Research leads | 0 |
| Promotion allowed | 0 |

Top diagnostics:

| Factor | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Mono | Turnover | FDR | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `gap_up_intraday_fade_10` | 20 | -0.0253 | -0.167 | -8.60 | 41.3% | -0.0154 | -0.600 | 5.2% | yes | no |
| `gap_up_intraday_fade_10` | 5 | -0.0195 | -0.136 | -7.01 | 42.7% | -0.0073 | -0.600 | 5.1% | yes | no |
| `intraday_momentum_20` | 20 | -0.0181 | -0.120 | -6.17 | 47.1% | 0.0009 | 0.100 | 3.8% | yes | no |
| `gap_down_intraday_recovery_10` | 20 | -0.0173 | -0.113 | -5.82 | 47.2% | 0.0012 | 0.100 | 3.5% | yes | no |
| `gap_reversal_lowvol_liquid_20` | 20 | -0.0174 | -0.112 | -5.76 | 45.4% | 0.0177 | 0.600 | 6.4% | yes | no |
| `gap_extreme_avoidance_20` | 20 | 0.0148 | 0.094 | 4.84 | 52.2% | 0.0624 | 0.900 | 3.4% | yes | no |

## Interpretation

This family produced statistically visible but weak signals. The strongest absolute IC came from `gap_up_intraday_fade_10`, but it was negative and had weak stability. Inverting it would not be promotion evidence: the inverse would still have ICIR only about `0.167`, below the `0.30` research threshold and far below the `0.50` stronger-factor threshold.

`gap_extreme_avoidance_20` had a clean-looking quantile spread and monotonicity, but its IC was only `0.0148`, below the `0.02` minimum. Treat it as a risk-filter hint at most, not an alpha lead.

## Decision

- Research leads: 0.
- Paper-ready/promotable factors: 0.
- Portfolio grid allowed: no.
- Negative-direction tuning allowed: no, not without a fresh pre-registered thesis and stronger ICIR evidence.
- Next direction: `round110_family_rotation_after_overnight_intraday_gap_failure`.

The family is hibernated for standalone alpha mining. Future work should rotate to another public-reference source with different information content rather than tuning overnight/intraday gap parameters.
