# CN Stock Tushare Fina Indicator Backfill Plan Round91 - 2026-06-21

## Executive Summary

Round91 produced no new factor and no profitability claim. Its useful output is a reusable planning-only guardrail for long-history Tushare `fina_indicator` backfill, so the project can move from a one-symbol PIT smoke test toward real profitability and quality factors without jumping into an uncontrolled full-market download.

Scope:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market: CN A-share stocks, not ETF rotation
- Safety: research-to-review only; no broker, account, order, or live-trading action

## What Was Built

New reusable code:

- `src/quant_robot/ops/fina_indicator_backfill_plan.py`
- `scripts/run_fina_indicator_backfill_plan.py`

New tests:

- `tests/unit/test_fina_indicator_backfill_plan.py`
- `tests/unit/test_fina_indicator_backfill_plan_cli.py`

New governance documents:

- `docs/superpowers/specs/2026-06-21-round91-fina-indicator-backfill-design.md`
- `docs/superpowers/plans/2026-06-21-round91-fina-indicator-backfill-plan.md`

Startup gate update:

- Allowed family added: `financial_profitability_quality`
- Next direction: `round92_tushare_fina_indicator_limited_symbol_backfill_smoke`
- Rejected routes added:
  - `full_universe_fina_indicator_backfill_without_limited_smoke`
  - `profitability_factor_mining_before_backfill_readiness_audit`

## Round91 Smoke Plan Result

Command:

```powershell
python scripts\run_fina_indicator_backfill_plan.py --symbols 000001.SZ,600519.SH --start-period 2015-03-31 --end-period 2025-12-31 --batch-size 20 --max-requests 200 --output-dir data\reports\fina_indicator_backfill_plan_round91_20260621
```

Result:

| Metric | Value |
|---|---:|
| Symbols | 2 |
| Quarterly periods | 44 |
| Total planned requests | 88 |
| Batches | 5 |
| Batch size | 20 |
| Blockers | 0 |
| Planner calls Tushare | false |
| Final holdout touched | false |

The plan starts at `20150331` and ends at `20251231`.

## Full-Universe Scale Estimate

Local `stock_basic` metadata currently has 5,529 listed A-share symbols. A full current-symbol `fina_indicator` backfill across 44 quarters would require about:

```text
5,529 symbols * 44 quarters = 243,276 Tushare requests
```

The cleaner long-cycle stock universe used in earlier authority-bar work had 4,725 assets, implying a cleaner tradable-universe estimate of:

```text
4,725 assets * 44 quarters = 207,900 requests
```

This is large enough that the next step must be a limited-symbol live smoke with resume and rate-limit behavior verified before any full-universe attempt.

## Research Decision

Round91 is accepted as data-pipeline/governance progress, not factor progress.

Current factor status remains:

- Promotable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- New Round91 factor candidates: 0

The work is still valuable because it removes a major blind spot: profitability and quality factors now have a concrete path toward PIT financial input coverage.

## Next Direction

Round92 should run a limited-symbol long-history `fina_indicator` backfill smoke:

- Use a small explicit symbol list covering SZ, SH, and if kept in scope, BJ suffixes.
- Cover 2015-03-31 through 2025-12-31.
- Keep resume enabled.
- Enforce a request budget and rate-limit policy.
- Run the PIT readiness audit after the smoke.
- Do not pre-register profitability factors until the smoke passes and the processed dataset is ready.
