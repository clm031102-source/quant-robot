# CN Stock Round129-131 Three-Round Review - 2026-06-22

## Scope

This review covers the three rounds after the Round126-128 review:

- Round129: Alpha101 rank PV reversal reference de-duplication.
- Round130: Alpha101 rank PV reversal residual prescreen.
- Round131: daily-basic non-price public carry preregistration.

This is required by the project rule: after every three factor-mining rounds, audit the previous work and adjust direction before continuing.

## Round Results

| Round | Direction | Main Evidence | Decision |
|---|---|---|---|
| 129 | Alpha101 rank PV reversal de-dup | High redundancy to existing PV reversal references; 2023 yearly IC failure remained visible | 0 promoted; no direct portfolio grid |
| 130 | Residualize Alpha101/PV lead | Residual IC mean -0.0323, ICIR -0.199, t-stat -10.21, IC positive rate 39.0%, 10/11 yearly failures | PV/Alpha101 reversal cluster hibernated |
| 131 | Daily-basic-only non-price carry/value preregistration | 10 candidates, 5 families, known local daily-basic fields only, 0 portfolio permission | Advance only to coverage preflight and prescreen |

## Low-Turnover Question Audit

The user's concern about the two strong low-turnover factors was valid. They were not worthless:

- `turnover_rate_low`: total return +5127.61%, annualized 21.25%, Sharpe 1.983, max drawdown -18.43%.
- `turnover_rate_f_low`: total return +5318.72%, annualized 19.86%, Sharpe 1.872, max drawdown -28.56%.

But the later audit chain explains why they still cannot be promoted:

- Round122 separated drawdown tolerance from capacity and data-quality gates.
- Round124 found small-capital IC/quantile evidence for a continuous participation-budget repair.
- Round126 costed TopN conversion rejected all 12 cases. Best overlap-adjusted Sharpe was only 0.226, max drawdown was around -69.55% or worse, and extreme-trade diagnostics were too large.

Conclusion: a 30% drawdown tolerance does not justify a factor whose costed portfolio path draws down roughly 70% and depends on extreme trade artifacts.

## What Worked

- The process did not keep blindly mining moneyflow or price-volume after redundancy was proven.
- The residual test in Round130 gave a clean reason to stop the Alpha101/PV line.
- Round131 registered a new family using only fields that actually exist locally: valuation, dividend/yield, share-structure, size/capacity, and volume-ratio crowding.
- No portfolio or promotion claim was made from preregistration.

## What Did Not Work

- Round129 and Round130 still spent effort on a price-volume cluster that had already looked crowded. The residual audit was necessary, but it should be the final check for that cluster.
- The daily-basic line still has a data-coverage risk. Local daily-basic input coverage must be audited before any IC claim.
- None of these three rounds produced a promotable or paper-ready factor.

## Counts

| Category | Count |
|---|---:|
| New preregistered Round131 candidates | 10 |
| New Round131 empirical factor claims | 0 |
| Promotable factors from Rounds129-131 | 0 |
| Paper-ready factors from Rounds129-131 | 0 |
| Manual/live usable factors | 0 |
| Families hibernated | 3 |

Hibernated families:

- `alpha101_rank_pv_reversal`
- `pv_reversal_cluster`
- `low_turnover_repair`

## Direction Adjustment

Next direction:

`round132_daily_basic_non_price_public_carry_prescreen`

Round132 must begin with:

1. daily-basic coverage preflight by field/date/cross-section;
2. same-date signal and next-bar label alignment audit;
3. IC, ICIR, t-stat, IC positive rate;
4. quantile spread and monotonicity;
5. factor turnover and capacity participation diagnostics;
6. redundancy check against prior daily-basic/QVM/value failures;
7. multiple-testing accounting across all 10 Round131 candidates.

No portfolio grid is allowed before at least one candidate passes the Round132 statistical and coverage prescreen.

## Stop-Loss Rule For Next Round

If Round132 shows poor daily-basic coverage or zero statistically credible leads after multiple-testing correction, stop this family immediately and rotate to a different public, nonredundant thesis rather than tuning parameters.
