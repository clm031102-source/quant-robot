# Round555 Next Steps Checklist

Use this after pulling `codex/factor-batch-cn-stock-round555-20260705`.

## Current State

- Startup gate packet validation is aligned with downstream strict validators.
- Candidate plan gate clears for 12 local daily-basic source-readiness candidates.
- Short local smoke completed for 2024-01-02 to 2024-01-31.
- Data manifest for the combined root remains `review_required` because of known data-quality warnings.
- No candidate is promoted; portfolio grid and promotion remain disabled by the candidate plan.

## Recommended Next Work

1. Add an alpha-factory candidate-plan packet validator so `run_tushare_alpha_factory.py` can require the executed factor names to match a cleared preregistration packet.
2. Rerun daily-basic smoke over a longer discovery window, still excluding 2026 final holdout.
3. Treat size-like fields (`total_mv_log`, `circ_mv_log`) as style diagnostics unless residualized exposure evidence is added.
4. Keep value/yield candidates (`ps_ttm_inverse`, `dv_ttm`, `pe_ttm_inverse`, `pb_inverse`) out of promotion until long-cycle replay, capacity, regime, and style-neutral gates pass.

## Still Forbidden

- Broker connection.
- Live account reads.
- Order placement.
- Automatic live trading.
- Promotion claims from short-window smoke evidence.
- Final-holdout reads unless a promotion gate explicitly requires and allows them.
- Committing generated `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
