# CN Stock Round448 Entry-Known Attribute Projection Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round448 tested whether simple entry-known trade attributes can improve the frozen long-sample low-turnover replacement baseline before spending more time on formal rebuilds.

This round deliberately avoided another broad parameter sweep. It tested a small, economically motivated set of attributes available at entry time:

- valuation risk: `pb`, `pe_ttm`, `ps_ttm`;
- turnover/capacity risk: `turnover_rate_f`, `participation_rate`, `circ_mv`;
- tradeability/board structure: `entry_allowed`, `stock_market`;
- dividend availability: `dv_ttm`.

## Method

Input baseline:

- `data/reports/round339_24h_profit_sprint_replacement_filters_voltarget_wrappers_20260627/replace_drop_turnover_f_low10_vol_target_6_lb84_exit_date_returns.csv`

Trade attributes:

- `data/reports/round338_24h_profit_sprint_turnover_low_replacement_filters_quarantine_corrected_20260627/replace_drop_turnover_f_low10_trades_with_tradeability.parquet`

Outputs:

- Projection audit: `data/reports/round448_24h_profit_sprint_entry_known_attribute_projection_20260627`
- Block audit: `data/reports/round448_24h_profit_sprint_entry_known_attribute_block_audit_20260627`
- Incremental robustness audit: `data/reports/round448_24h_profit_sprint_entry_known_attribute_incremental_robustness_20260627`

Process improvement added in this round:

- `src/quant_robot/ops/shortlist_incremental_return_robustness.py`
- `scripts/run_shortlist_incremental_return_robustness.py`
- `tests/unit/test_shortlist_incremental_return_robustness.py`
- `tests/unit/test_shortlist_incremental_return_robustness_cli.py`

The new tool audits candidate return streams against a base stream using full-sample deltas, chronological CPCV-style splits, quarterly block-bootstrap paths, and yearly delta rows.

## Main Results

Baseline:

- annualized return 6.352%;
- total return +177.08%;
- overlap Sharpe 0.517;
- max drawdown -28.88%;
- win rate 41.13%.

Top projection candidates versus the same frozen template:

| Candidate | Meaning | Delta Ann. | Delta Total | Delta Overlap | Delta DD | CPCV Ann Win | Bootstrap Ann Win | Bootstrap Overlap Win | Bootstrap DD Win | Year Win |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `ps_gt10` | cash selected trades with `ps_ttm > 10` | +0.186% | +8.11% | +0.054 | +1.81% | 67.50% | 62.20% | 94.10% | 97.20% | 72.73% |
| `pb_gt6` | cash selected trades with `pb > 6` | +0.160% | +7.00% | +0.042 | +0.27% | 58.33% | 64.20% | 90.30% | 92.30% | 63.64% |
| `pe_gt100` | cash selected trades with `pe_ttm > 100` | +0.114% | +4.93% | +0.087 | +4.55% | 56.67% | 56.00% | 99.90% | 100.00% | 36.36% |
| `pb_gt4` | cash selected trades with `pb > 4` | +0.106% | +4.61% | +0.108 | +1.97% | 55.83% | 55.50% | 93.10% | 98.00% | 63.64% |

Rejected or defensive-only observations:

- `circ_mv_gt5000k`, `turnover_f_lt1`, `turnover_f_gt5`, `dv_missing`, `participation_gt0004`, and `circ_mv_lt500k` reduce annualized return or fail the incremental annualized-win gates.
- `circ_mv_lt500k` is particularly bad for return: annualized delta -2.872% and total-return delta -100.94%, despite lower drawdown.

## Interpretation

The useful signal is not a strong standalone profitability factor. It is a small valuation-risk filter.

`ps_gt10` and `pb_gt6` are the only two projection leads worth keeping in memory. They improve full-sample return slightly, win a majority of CPCV/bootstrap annualized comparisons, and improve overlap/drawdown in most bootstrap paths.

The edge is still too thin for promotion:

- annualized uplift is only about 0.16% to 0.19%;
- 2025 alone adds almost no incremental return;
- `ps_gt10` loses in 2019 and 2023;
- `pb_gt6` loses in 2019-2021 and slightly in 2025;
- this is still projection evidence, not a formal cohort-entry rebuilt event stream.

## Decision

Do not add any Round448 candidate to the active paper-simulation handoff set.

Keep `ps_gt10` and `pb_gt6` as projection-only valuation risk-filter leads. They may be revisited only if a future formal simulation lane needs an entry-known valuation risk cap and the same-event-generator fair control is rerun.

Stop widening this valuation-filter grid now. The marginal return is too small for another threshold search.

## Next Direction

Rotate away from PB/PS/PE threshold tuning. The next mining work should test a genuinely different point-in-time family with stronger economic rationale, such as:

- residual low-volatility/liquidity reversal with industry/size controls;
- PIT earnings or forecast-revision timing where announcement dates are usable;
- tradeability/liquidity microstructure that explains execution losses rather than realized return tails.

Any next family must use the new incremental robustness audit before entering paper-simulation discussion.
