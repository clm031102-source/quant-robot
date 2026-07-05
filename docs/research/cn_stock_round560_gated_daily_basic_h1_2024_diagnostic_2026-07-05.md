# CN Stock Round560 Gated Daily-Basic H1 2024 Diagnostic

Date: 2026-07-05

Machine context: office desktop as the main work machine

Branch: `codex/factor-batch-cn-stock-round555-20260705`

Scope: run a longer gated daily-basic source-readiness diagnostic over 2024 H1 using the Round559 return/capacity summary fields.

## Gate Trace

The generated alpha-factory `manifest.json` contains:

| Packet | Path |
| --- | --- |
| Startup gate | `data\reports\factor_mining_startup_gate\factor_mining_startup_gate.json` |
| Data manifest | `data\reports\round555_cn_stock_data_manifest_combined_20260705\cn_stock_data_manifest.json` |
| Candidate-plan gate | `data\reports\round555_daily_basic_source_smoke_candidate_plan_gate_20260705\factor_mining_candidate_plan_gate.json` |

## Run Window

| Field | Value |
| --- | --- |
| Source | local processed bars |
| Data root | `data\processed\office_desktop_20260616_combined_research` |
| Factor source | `tushare_daily_basic` |
| Factor input root | `data\processed\office_desktop_20260617_daily_basic_factor_inputs\processed\factor_inputs` |
| Start | 2024-01-02 |
| End | 2024-06-28 |
| Cost | 10 bps |
| Top N | 5 |

## Summary

| Metric | Value |
| --- | ---: |
| Hypotheses | 12 |
| Completed | 12 |
| Adjusted-significant IC screens | 0 |
| Rejected after multiple testing | 12 |
| Alpha-factory internal paper-eligible rows | 0 |
| Positive total-return rows | 0 |
| Positive Sharpe rows | 0 |
| Capacity-limited rows | 7 |
| Paper-eligible positive-return rows | 0 |
| Paper-eligible negative-return rows | 0 |

Top rows:

| Rank | Factor | Adj p | ICIR | Sharpe | Total return | Capacity-limited trades | Internal eligible |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `circ_mv_log` | 1.000000 | 0.0413 | -1.3048 | -0.0882 | 0 | false |
| 2 | `total_mv_log` | 1.000000 | 0.0429 | -2.0036 | -0.1187 | 0 | false |
| 3 | `dv_ttm` | 1.000000 | 0.1130 | -2.0240 | -0.2302 | 0 | false |
| 4 | `ps_ttm_inverse` | 1.000000 | 0.0886 | -2.4673 | -0.2497 | 3 | false |
| 5 | `pe_ttm_inverse` | 1.000000 | 0.0585 | -2.5465 | -0.3401 | 14 | false |
| 6 | `volume_ratio` | 0.900409 | -0.1667 | -6.1353 | -0.8483 | 4 | false |
| 7 | `volume_ratio_low` | 0.900409 | 0.1667 | -6.1982 | -0.9071 | 237 | false |
| 8 | `pb_inverse` | 1.000000 | 0.1061 | -6.8399 | -0.7807 | 53 | false |
| 9 | `turnover_rate_f` | 0.085893 | -0.2519 | -6.8595 | -0.9087 | 0 | false |
| 10 | `turnover_rate` | 0.134152 | -0.2376 | -6.8912 | -0.8873 | 0 | false |
| 11 | `turnover_rate_low` | 0.134152 | 0.2376 | -8.9842 | -0.9457 | 256 | false |
| 12 | `turnover_rate_f_low` | 0.085893 | 0.2519 | -10.5168 | -0.9694 | 347 | false |

## Interpretation

- The longer H1 window removed the January-only adjusted-significant IC rows.
- The new summary fields make the rejection clearer: zero positive total-return rows, zero positive Sharpe rows, and seven capacity-limited rows.
- Size-like fields (`circ_mv_log`, `total_mv_log`) remain diagnostics only; they are not alpha candidates.
- Value and low-activity variants still show direct portfolio weakness and capacity issues under the simple TopN construction.

## Decision

Do not promote any daily-basic candidate. Do not spend the next round on daily-basic parameter widening or direction flips. The next useful work is either a style-exposure/residual diagnostic to explain the failure mode, or rotation to a new PIT-safe source family.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- No provider download.
- No final-holdout tuning.
- Generated `data/reports` artifacts remain out of Git.
