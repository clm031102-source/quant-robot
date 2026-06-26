# CN Stock Round104-106 Three-Round Review

## Scope

This review covers the required three-round audit after:

- Round104: capacity-safe trend/amount accumulation preregistration.
- Round105: long-cycle prescreen of the Round104 positive trend/amount direction.
- Round106: negative-IC anti-overheat preregistration.

## Round104 Summary

Round104 rotated away from the redundant Bollinger/RSI/Donchian/low-volatility reversal cluster and registered ten public trend, breakout, OBV-style, and amount accumulation candidates. It correctly blocked portfolio backtests and promotion before prescreen.

Useful output:

- 10 pre-registered candidates.
- Public reference tags included qlib, Alphalens, vectorbt, pyfolio, and WorldQuant-style price-volume ideas.
- Next gate was Round105 long-cycle prescreen.

## Round105 Summary

Round105 ran the full 2015-2025 long-cycle prescreen:

- Bar assets: 5,707
- Bar rows: 10,785,537
- Candidate count: 10
- Factor rows: 100,335,759
- Label rows: 21,417,227
- Aligned rows: 199,187,090
- Tests: 20
- FDR-significant tests: 20
- Research leads: 0
- Promotion allowed candidates: 0

Main finding: the positive trend/amount accumulation hypothesis failed, but it failed with unusually strong negative IC. The strongest examples were:

| Factor | Horizon | IC | ICIR | t-stat | IC>0 |
|---|---:|---:|---:|---:|---:|
| `accumulation_distribution_proxy_20` | 20 | -0.1005 | -0.681 | -34.93 | 24.0% |
| `money_pressure_efficiency_20` | 20 | -0.0952 | -0.709 | -36.36 | 23.6% |
| `volume_weighted_momentum_quality_20` | 20 | -0.0928 | -0.689 | -35.33 | 24.0% |
| `turnover_expansion_momentum_10_40` | 20 | -0.0899 | -0.639 | -32.76 | 26.0% |

Audit interpretation: this is not a capacity failure and not a promotion signal. It is direction evidence that high trend, high amount pressure, and late accumulation may identify overheated or crowded names.

## Round106 Summary

Round106 preregistered ten anti-overheat candidates:

- Candidate count: 10
- Unique names: 10
- Portfolio backtest allowed candidates: 0
- Promotion allowed candidates: 0
- Blockers: none
- Next required gate: `alphalens_style_ic_quantile_turnover_prescreen`

The registration explicitly labels Round105 as hypothesis evidence, not promotion evidence.

## Decision

The next direction is:

`round107_negative_ic_trend_accumulation_prescreen`

Rules for the next run:

- Run the same long-cycle prescreen before any portfolio grid.
- Do not promote any inverse candidate from Round105 or Round106 alone.
- Do not tune windows or weights before seeing the preregistered prescreen.
- Do not revisit the positive trend/amount direction unless a new public hypothesis materially changes the economics.

## Rejected Directions

- Positive trend/amount accumulation continuation after Round105 negative IC.
- Same-family parameter tuning after failed positive direction.
- Post-hoc inverse promotion from Round105 evidence.
- Negative-IC trend/amount portfolio grid before prescreen.

## Budget Judgment

This three-round block was productive despite producing zero promotable factors. The value is methodological: it prevented the office desktop from blindly tuning a failed positive trend family and converted a strong negative-IC observation into a controlled preregistered test. The next round should be a prescreen, not a backtest or top-N sweep.
