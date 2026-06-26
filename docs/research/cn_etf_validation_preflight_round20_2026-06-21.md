# CN ETF Validation Preflight Round 20

Date: 2026-06-21

## Purpose

Round 20 converted the Round 19 failure into a reusable guardrail.

Problem found in Round 19:

- The full-sample ETF candidate looked acceptable after a simple risk overlay.
- Walk-forward rejected it across 42 / 42 folds.
- The failure was partly predictable before running the expensive validation because the ETF universe was narrow and the regime filter left too few fold-level opportunities.

## New Project Tooling

Added:

- `src/quant_robot/ops/etf_validation_preflight.py`
- `scripts/run_etf_validation_preflight.py`
- `tests/unit/test_etf_validation_preflight.py`
- `tests/unit/test_etf_validation_preflight_cli.py`

Updated:

- `configs/workstations.json`

The `factor_validation` task description now records that CN ETF walk-forward reruns should run the ETF validation preflight first.

## What The Preflight Checks

The preflight blocks low-power ETF validation configs before expensive walk-forward runs.

Checks:

- ETF asset count
- walk-forward fold count
- rebalance opportunities per test fold
- regime-allowed rebalance dates per test fold
- zero-allowed-fold rate
- research-only live boundary

Default policy:

- minimum ETF assets: 12
- minimum rebalance opportunities per fold: 20
- minimum median regime-allowed rebalance dates: 20
- maximum zero-allowed-fold rate: 10%

## Applied To Round 19 Config

Command:

```powershell
python scripts\run_etf_validation_preflight.py --config configs\walk_forward_cn_etf_smart_money_exposure06_20260621.json --source processed-bars --data-root data\processed\etf_csv --output-dir data\reports\etf_validation_preflight_cn_etf_smart_money_exposure06_20260621 --allow-blocked
```

Result:

- Status: blocked
- Asset count: 10
- Date count: 3,507
- Fold count: 42
- Minimum rebalance opportunities: 26
- Median regime-allowed rebalance dates: 16
- Minimum regime-allowed rebalance dates: 0
- Zero-allowed folds: 7 / 42
- Zero-allowed fold rate: 16.67%

Blockers:

- `asset_count_below_minimum`
- `median_regime_allowed_rebalance_dates_below_minimum`
- `zero_allowed_fold_rate_above_limit`

## Interpretation

This preflight would have warned that the Round 19 walk-forward was statistically weak before the full run.

It does not prove a factor can make money. It improves capital and compute discipline by preventing low-power validation from being mistaken for a meaningful test.

## Decision

Use this preflight before future CN ETF walk-forward reruns.

Do not spend more validation budget on the current 10-ETF universe when the regime filter materially reduces fold-level opportunities.

## Next Direction

After the required Round 20 sync:

1. Expand or audit the CN ETF universe before more ETF walk-forward work.
2. Prefer ETF factors that trade often enough to clear fold-level opportunity checks.
3. Continue using public, economically interpretable families, but require preflight plus walk-forward before calling anything useful.
4. Avoid treating same-sample approvals as real discoveries.

## Current Conclusion

Round 20 produced 0 new factor names and 0 promotable factors.

It produced a reusable project guardrail that should reduce wasted factor-mining runs.
