# CN Stock Round325-327 Three-Round Audit

Date: 2026-06-27

Scope: 24h profit-factor sprint, office desktop, CN stock factor mining. This audit covers three completed rounds after the decision-date overlay fix:

- Round325: public bar indicators as direct long-only signals and bottom-exclusion risk filters.
- Round326: FIP bottom-exclusion filter applied to the low-turnover lead.
- Round327: daily-basic value/yield, residual, public QVM, and low-turnover liquidity/size repair variants under the clean portfolio diagnostic.

Safety boundary: research-to-review only. No broker connection, account reads, orders, or live trading.

## Round325 Result

Output: `data/reports/round325_24h_profit_sprint_public_bar_avoidance_bottom_exclusion_20260627`

The public technical indicator family did not produce a tradable long-only factor. The best relative risk-filter lead was:

| Factor | Classification | Total | Annual | Sharpe | Overlap Sharpe | Max DD | Win | Relative | Positive relative folds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `fip_discrete_jump_reversal_20_5` | research lead risk filter | +11.83% | +0.41% | 0.090 | 0.050 | -70.96% | 44.33% | +33.27% | 11/11 |

Interpretation:

- This is not a profit factor by itself. The absolute return, Sharpe, and drawdown are too weak.
- The only useful clue is relative: excluding the worst FIP bucket consistently beat its all-eligible benchmark across yearly folds.
- This made it worth one follow-up test as a filter on the stronger low-turnover lead.

## Round326 Result

Output: `data/reports/round326_24h_profit_sprint_turnover_low_fip_discrete_exclusion_filter_20260627`

Applying the FIP bottom-exclusion filter to `turnover_rate_low` worsened the strategy:

| Case | Total | Annual | Sharpe | Overlap Sharpe | Max DD | Win |
|---|---:|---:|---:|---:|---:|---:|
| No FIP filter, Top50 | +151.32% | +5.73% | 0.614 | 0.319 | -45.79% | 50.24% |
| Exclude bottom 10%, Top50 | +80.51% | +3.64% | 0.407 | 0.222 | -54.26% | 47.60% |
| Exclude bottom 20%, Top50 | +80.18% | +3.62% | 0.402 | 0.222 | -54.37% | 47.84% |
| Exclude bottom 30%, Top50 | +81.73% | +3.61% | 0.401 | 0.220 | -56.50% | 47.17% |

Interpretation:

- The FIP filter was a broad risk-avoidance clue, not a useful overlay for the existing low-turnover signal.
- It removed or delayed too many profitable low-turnover selections and did not reduce drawdown.
- The line should be frozen unless reused as an independent regime/risk diagnostic, not as a low-turnover filter.

## Round327 Result

Output: `data/reports/round327_24h_profit_sprint_daily_basic_value_turnover_composite_clean_20260627`

The clean portfolio diagnostic tested 14 factor names and 56 parameter combinations across Top50/100 and 5/10 bps cost. No case passed.

Best by overlap-adjusted Sharpe per factor:

| Factor | Best case | Total | Annual | Sharpe | Overlap Sharpe | Max DD | Win | Pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `turnover_rate_low` | Top50, cost5 | +151.32% | +5.73% | 0.614 | 0.319 | -45.79% | 50.24% | no |
| `daily_basic_value_yield_size_neutral_20` | Top50, cost5 | +111.90% | +4.83% | 0.507 | 0.272 | -49.12% | 53.18% | no |
| `turnover_rate_f_low` | Top100, cost5 | +97.10% | +3.17% | 0.382 | 0.204 | -51.01% | 49.32% | no |
| `turnover_rate_low_adv_blend_mv_bucket_rank` | Top100, cost5 | +59.05% | +2.22% | 0.267 | 0.147 | -58.35% | 50.42% | no |
| `turnover_rate_low_liquid_mv_bucket_rank` | Top50, cost5 | +21.50% | +1.13% | 0.155 | 0.083 | -66.96% | 46.58% | no |

Main blockers:

- Drawdown remains far below the -35% sprint floor.
- Overlap-adjusted Sharpe is weak after correcting for overlapping holding windows.
- Technical liquidity/size repair variants reduce the low-turnover edge rather than repairing it.
- Value/yield is economically plausible and second-best, but not strong enough as a standalone profit factor.
- Residual, public QVM, and risk-repair variants were mostly negative under this clean portfolio setup.

## Diagnosis

The last three rounds show that the problem is not just "bad parameters." The current CN stock full-sample research has three structural issues:

1. Public price/volume indicators are mostly acting as broad risk screens, not alpha generators.
2. Low-turnover still contains the strongest positive long-cycle clue, but the return comes with deep market-regime drawdowns.
3. Simple liquidity, size, value, low-volatility, and FIP filters dilute the signal without materially reducing drawdown.

This means the next sprint should not keep mutating low-turnover filters. The better path is to change the research object:

- Separate alpha discovery from portfolio construction.
- Test non-price event/accounting families with point-in-time lag discipline.
- Add industry/style neutralization and market-state risk budgeting at the portfolio level.
- Use low-turnover only as a benchmark or weak component, not as the main family to mutate.

## Next Direction

Priority for the next block:

1. Accounting/event family audit: announcement-lagged profitability, growth surprise, revisions, buyback/dividend, shareholder and unlock event features if available.
2. Portfolio construction repair: industry caps, drawdown budget, volatility target, and stop/re-entry rules tested through walk-forward selection.
3. Factor exposure decomposition: determine whether the surviving low-turnover/value signals are just market, size, or liquidity beta.

Promotion stance after Round325-327:

- Simulation-ready factors: 0.
- Paper-ready factors: 0.
- Research leads retained: `turnover_rate_low` pipeline, `daily_basic_value_yield_size_neutral_20` as a weak economic component, `fip_discrete_jump_reversal_20_5` only as a relative risk-diagnostic clue.
- Frozen lines: standalone public bar indicators, FIP filter on low-turnover, low-turnover liquidity/size bucket repairs.
