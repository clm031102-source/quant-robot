# CN Stock Round558 Gated Daily-Basic January Smoke

Date: 2026-07-05

Machine context: office desktop as the main work machine

Branch: `codex/factor-batch-cn-stock-round555-20260705`

Scope: rerun the January 2024 local daily-basic alpha-factory smoke with the new candidate-plan gate requirement and manifest gate trace enabled.

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
| End | 2024-01-31 |
| Cost | 10 bps |
| Top N | 5 |

## Summary

| Metric | Value |
| --- | ---: |
| Hypotheses | 12 |
| Completed | 12 |
| Adjusted-significant IC screens | 6 |
| Rejected after multiple testing | 6 |
| Alpha-factory internal paper-eligible rows | 3 |

Top rows:

| Rank | Factor | Adj p | ICIR | Sharpe | Total return | Capacity-limited trades | Internal eligible |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `ps_ttm_inverse` | 0.008241 | 0.7788 | -3.3225 | -0.0800 | 0 | true |
| 2 | `dv_ttm` | 0.001082 | 0.8983 | -3.5900 | -0.0792 | 0 | true |
| 3 | `volume_ratio` | 0.039515 | 0.6742 | -8.3860 | -0.3195 | 0 | true |
| 4 | `circ_mv_log` | 0.219950 | 0.5412 | 1.0061 | 0.0133 | 0 | false |
| 5 | `total_mv_log` | 0.341744 | 0.5026 | -0.6901 | -0.0095 | 0 | false |
| 6 | `turnover_rate_low` | 0.441393 | 0.4791 | -3.2834 | -0.0707 | 24 | false |
| 7 | `pb_inverse` | 0.005928 | 0.7993 | -5.2885 | -0.1480 | 4 | false |
| 8 | `pe_ttm_inverse` | 0.000281 | 0.9703 | -5.5509 | -0.1021 | 11 | false |
| 9 | `volume_ratio_low` | 0.039515 | -0.6742 | -6.1822 | -0.2034 | 22 | false |
| 10 | `turnover_rate` | 0.441393 | -0.4791 | -7.9119 | -0.3183 | 0 | false |
| 11 | `turnover_rate_f` | 0.300641 | -0.5140 | -11.3729 | -0.4777 | 0 | false |
| 12 | `turnover_rate_f_low` | 0.300641 | 0.5140 | -11.9249 | -0.1792 | 42 | false |

## Interpretation

- The Round557 gate trace is working on the full January smoke.
- Short-window IC strength does not translate into acceptable portfolio evidence here.
- The three internal eligible rows all have negative January total return and negative Sharpe, so they remain source-readiness observations only.
- `pb_inverse`, `pe_ttm_inverse`, `volume_ratio_low`, and `turnover_rate_f_low` are blocked by capacity-limited trades despite some IC strength.
- Size-like fields remain style diagnostics, not alpha claims.

## Decision

Do not promote any Round558 candidate. The next useful research step is a longer discovery-window diagnostic that reports style exposure and capacity blockers explicitly before any walk-forward or long-cycle replay.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- No provider download.
- No final-holdout tuning.
- Generated `data/reports` artifacts remain out of Git.
