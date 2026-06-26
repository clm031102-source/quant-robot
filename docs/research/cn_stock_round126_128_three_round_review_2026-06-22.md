# CN Stock Three-Round Review - Rounds 126-128

## Reviewed Rounds

- Round126: turnover repair champion portfolio conversion.
- Round127: public reference multi-family preregistration.
- Round128: public reference multi-family prescreen.

## What Changed

Round126 closed the low-turnover repair line. It showed high headline total return, but zero walk-forward candidates after overlap, drawdown, calendar, extreme-trade, and capacity gates. This prevented another round of polishing a non-tradable low-turnover anomaly.

Round127 rotated away from the failed family and preregistered 20 candidates across 9 public-reference families. Public projects were used as hypothesis sources only, not as proof.

Round128 ran the full long-cycle prescreen across 2015-01-05 to 2023-07-31. It counted all 20 candidates and all three horizons in multiple-testing accounting.

## Results

- New candidates preregistered in Round127: 20.
- Families covered: 9.
- Round128 factor x horizon tests: 60.
- FDR-significant tests: 54.
- Unique research lead factors: 1.
- Research lead horizon rows: 3.
- Promotable factors: 0.
- Portfolio-grid permission: 0.

## Best Evidence

`alpha101_rank_pv_reversal_liquid_20` is the only positive research lead:

- 20d: IC 0.0489, ICIR 0.526, t-stat 23.85, IC positive rate 69.1%, Q5-Q1 0.0089.
- 10d: IC 0.0453, ICIR 0.496, t-stat 22.55, IC positive rate 69.8%, Q5-Q1 0.0057.
- 5d: IC 0.0431, ICIR 0.471, t-stat 21.44, IC positive rate 68.4%, Q5-Q1 0.0037.

## Main Risks

- The three positive lead rows are the same factor across horizons, not three independent factors.
- No costed portfolio, walk-forward, or regime proof exists yet.
- Several public trend/breakout factors are strongly negative, which creates post-hoc inverse-factor temptation.
- Alpha101-style price-volume reversal may overlap with earlier price-volume reversal clusters and must be de-duplicated.

## Decision

Next work must be review and audit before any new mining or portfolio grid:

1. De-duplicate `alpha101_rank_pv_reversal_liquid_20` against existing price-volume reversal and Alpha101 references.
2. Audit negative-sign public trend/breakout evidence as a separate preregistration question, not a direct promotion.
3. Decide whether the next empirical round should be lead de-duplication, inverse-direction preregistration, or a fresh non-price-volume family.
4. Keep promotion blocked until walk-forward, cost/capacity, regime coverage, and portfolio conversion gates pass.
