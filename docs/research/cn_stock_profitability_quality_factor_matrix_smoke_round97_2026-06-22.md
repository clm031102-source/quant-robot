# CN Stock Profitability Quality Factor Matrix Smoke Round97 - 2026-06-22

## Executive Summary

Round97 converted the 14 Round96 pre-registered profitability-quality candidates into factor values and aligned them to forward-return labels using local CN stock bars. The smoke passed with zero alignment violations.

This is a necessary anti-lookahead checkpoint, not a profitability result. No IC, Sharpe, profit rate, win rate, or portfolio return was claimed.

## Scope

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Financial root: `data/processed/tushare_fina_indicator_shard1_full100_backfill_round95_20260622`
- Preregistration: `data/reports/profitability_quality_preregistration_round96_20260622/profitability_quality_preregistration.json`
- Bars roots:
  - `data/processed/cn_stock_long_history_2015_202306`
  - `data/processed/office_desktop_20260616_combined_research`
- Horizons: 5 and 20 trading days
- Execution lag: 1 trading day

## Command

```powershell
python scripts\run_profitability_quality_factor_matrix_smoke.py --financial-root data\processed\tushare_fina_indicator_shard1_full100_backfill_round95_20260622 --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --preregistration-json data\reports\profitability_quality_preregistration_round96_20260622\profitability_quality_preregistration.json --output-dir data\reports\profitability_quality_factor_matrix_smoke_round97_20260622 --horizon 5 --horizon 20 --execution-lag 1 --min-label-coverage 0.80
```

## Result

| Metric | Value |
|---|---:|
| Candidates | 14 |
| Financial events | 4,328 |
| Events with signal date | 4,327 |
| Bar assets | 100 |
| Bar rows | 266,894 |
| Factor value rows | 58,711 |
| Label aligned rows | 117,394 |
| Label coverage | 96.89% |
| Alignment violation rows | 0 |
| Blockers | 0 |

Candidate-level label coverage was 100.00% for every candidate after excluding rows where the candidate itself had no valid factor value.

## Research Decision

Round97 is accepted as factor-matrix and label-alignment progress.

Current factor status:

- Promotable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Pre-registered profitability-quality candidates: 14
- Candidates with clean label-aligned matrix smoke: 14

The next round may run a controlled IC screen. It still may not run promotion, portfolio claims, or parameter tuning.

## Next Direction

```text
round98_profitability_quality_controlled_ic_screen_on_clean_shard
```

Required gates:

- Spearman IC by report period or signal cohort;
- minimum cross-section size per IC observation;
- multiple-testing accounting over 14 candidates and all horizons;
- no parameter tuning after seeing IC;
- no promotion without long-cycle, walk-forward, cost, capacity, and portfolio translation checks.
