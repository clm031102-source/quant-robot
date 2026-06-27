# CN Stock Round394 - Daily-Basic Filters on Dragon-Hot

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round394 tested whether public daily-basic fields can identify bad entries inside the already-useful Dragon-Tiger hot-chase lane.

This is not a direct TopN value/quality portfolio. The test starts from the frozen `cash_dragon_hot_chase_20d` official template, excludes trades already cashed by the Dragon-Hot filter, then cashes selected entries by daily-basic ranks inside the remaining selected basket.

## Outputs

- Factor source and official-template projection: `data/reports/round394_24h_profit_sprint_daily_basic_on_dragon_hot_projection_20260627`
- Wrapped event returns: `data/reports/round394_24h_profit_sprint_daily_basic_on_dragon_hot_vt6_zz500_projection_20260627`
- OOS split: `data/reports/round394_24h_profit_sprint_daily_basic_on_dragon_hot_oos_20260627`
- Block audit: `data/reports/round394_24h_profit_sprint_daily_basic_on_dragon_hot_block_audit_20260627`
- Beta audit: `data/reports/round394_24h_profit_sprint_daily_basic_on_dragon_hot_beta_audit_20260627`

## Tested Fields

`ps_ttm`, `pe_ttm`, `pb`, `volume_ratio`, `dv_ttm`, `circ_mv`, `total_mv`, `turnover_rate_f`, and `turnover_rate`.

Coverage was good enough for this screen. PS, PB, size, turnover, and volume ratio were effectively fully covered. PE missed 12.38% on the post-Dragon-Hot candidate universe and dividend missed 19.34%.

## Main Results

The family did not improve high-return performance.

| Candidate | Wrapped Ann. | Overlap Sharpe | Max DD | Mean OOS Ann. | Worst OOS DD | Decision |
|---|---:|---:|---:|---:|---:|---|
| `dragon_hot_100` | 6.45% | 0.532 | -28.57% | 8.02% | -23.68% | keep as higher-return reference |
| `ps_dragon_100` | 5.72% | 0.569 | -23.60% | 6.88% | -19.48% | defensive observation only |
| `turnoverf_dragon_100` | 5.30% | 0.534 | -24.92% | 6.62% | -20.18% | reject |

The PS filter is the only useful signal in this round. It reduces drawdown and improves overlap-adjusted Sharpe, but it gives up return.

## Blocker

`cash_public_ps_top20` has a small official-template projection blocker:

- missing factor share: 0.0077%;
- unmatched absolute flagged contribution: 0.0120;
- configured limit: 0.005.

This is not large enough to ignore, but it is also not a data-coverage failure. Any shortlist use must remain observation-only until the projection tolerance or calendar-matching path is explicitly repaired.

## Decision

Do not add raw daily-basic filters as high-return alpha enhancers.

Advance only the PS defensive line to Round395 self-risk testing, because it may be useful as a low-drawdown simulation profile.
