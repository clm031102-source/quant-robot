# CN Stock Daily-Basic Non-Price Public Carry Preregistration Round131 - 2026-06-22

## Scope

Round131 follows the Round130 Alpha101/PV residual failure and the user's drawdown-tolerance question about the two high-return low-turnover factors.

The low-turnover line was not ignored:

- Round122 classified `turnover_rate_low` and `turnover_rate_f_low` as real high-return research leads, not junk.
- Round124 found small-capital IC/quantile leads after continuous participation-budget repair.
- Round126 converted the single frozen champion into a costed TopN portfolio and rejected all 12 cost/capital cases. The best total return was still high, but overlap-adjusted Sharpe was only 0.226, max drawdown reached roughly -69.55% or worse, and extreme-trade diagnostics remained too large.

Conclusion: a 30% drawdown tolerance is not a capacity or data-quality waiver. The low-turnover family stays hibernated unless a new nonredundant economic thesis appears.

New artifact:

`data/reports/daily_basic_non_price_public_carry_preregistration_round131_20260622`

## Data Field Discipline

Before registering candidates, the local daily-basic input schema was checked. Available fields include:

`pe`, `pe_ttm`, `pb`, `ps`, `ps_ttm`, `dv_ratio`, `dv_ttm`, `total_share`, `float_share`, `free_share`, `total_mv`, `circ_mv`, and `volume_ratio`.

Round131 deliberately blocks:

- `turnover_rate` / `turnover_rate_f` backdoors;
- Alpha101 / PV / moneyflow continuation;
- bar fields such as price, high/low, and amount inside the signal formula;
- portfolio backtest or promotion before daily-basic coverage preflight.

## Result

| Metric | Value |
|---|---:|
| Candidates preregistered | 10 |
| Families | 5 |
| Portfolio permission | 0 |
| Promotion permission | 0 |
| Blockers | 0 |
| Next gate | `round132_daily_basic_non_price_public_carry_prescreen` |

## Candidates

| Factor | Family | Required fields |
|---|---|---|
| `daily_basic_dividend_value_stability_carry_20` | dividend value carry | `dv_ttm`, `dv_ratio`, `pb`, `pe_ttm` |
| `daily_basic_value_yield_size_neutral_20` | dividend value carry | `pe_ttm`, `pb`, `ps_ttm`, `dv_ttm`, `circ_mv` |
| `daily_basic_valuation_reversion_quality_60` | valuation stability | `pb`, `ps_ttm`, `dv_ttm` |
| `daily_basic_valuation_dispersion_compression_60` | valuation stability | `pb`, `pe_ttm`, `dv_ratio` |
| `daily_basic_free_float_supply_quality_20` | share-structure quality | `free_share`, `float_share`, `total_share`, `pb` |
| `daily_basic_float_structure_value_blend_20` | share-structure quality | `free_share`, `float_share`, `pb`, `dv_ttm` |
| `daily_basic_volume_ratio_crowding_reversal_20` | crowding balance | `volume_ratio`, `pb`, `dv_ttm` |
| `daily_basic_crowding_value_yield_balance_20` | crowding balance | `volume_ratio`, `ps_ttm`, `dv_ratio` |
| `daily_basic_midcap_value_yield_capacity_20` | capacity-aware value | `dv_ttm`, `pb`, `ps_ttm`, `circ_mv` |
| `daily_basic_size_quality_value_stability_60` | capacity-aware value | `pb`, `dv_ttm`, `total_mv`, `pe_ttm` |

## Interpretation

This round does not discover a profitable factor. It improves the mining process:

- It rotates away from a disproved price-volume residual line.
- It respects the low-turnover evidence instead of pretending the raw return is promotable.
- It uses only fields already present in the local daily-basic input store.
- It forces Round132 to start with coverage, field availability, IC, quantile spread, turnover, capacity, family redundancy, and multiple-testing checks.

## Decision

Promotion status:

- Promotable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Research candidates preregistered for prescreen: 10

Next direction:

`round132_daily_basic_non_price_public_carry_prescreen`

Required next checks:

- daily-basic field coverage by date and cross-section;
- same-date signal / next-bar label alignment;
- long-cycle IC and ICIR where coverage allows;
- quantile monotonicity and Q5-Q1 spread;
- turnover and capacity diagnostics;
- family redundancy against prior value/QVM/daily-basic failures;
- multiple-testing accounting across all 10 candidates;
- no portfolio grid before a prescreen lead exists.
