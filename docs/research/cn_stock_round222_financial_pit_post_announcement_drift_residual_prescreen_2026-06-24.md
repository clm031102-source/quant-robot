# CN Stock Round222 Financial PIT Post-Announcement Drift Residual Prescreen

Date: 2026-06-24

## Purpose

This round tested the 7 pre-registered financial PIT post-announcement drift candidates after the matrix/label smoke passed. The screen used 2015-01-01 through 2025-12-31 data, excluded the 2026 final holdout, aligned factor dates to the first tradable date after event-day reaction, and evaluated IC, quantile shape, industry/size/liquidity neutral survival, multiple testing, and static profitability reference de-duplication.

## Command

```powershell
python scripts\run_financial_pit_post_announcement_drift_residual_prescreen.py --output-dir data\reports\financial_pit_post_announcement_drift_residual_prescreen_round222_20260624 --allow-not-ready
```

## Result

- Passes: True as an engineering/research screen.
- Candidates: 7
- Tests: 14
- Factor rows: 28,802
- Aligned rows: 57,604
- IC observation dates: 30 for most candidates; 13 for late-announcer candidates.
- Multiple-testing lead count: 1
- Neutral gate pass count: 0
- Research lead count: 0
- Promotion allowed candidates: 0
- Max factor date: 2025-11-12
- Max label date: 2025-12-23
- Reference de-dup pass count: 14

## Best Diagnostic Signal

The only multiple-testing significant result was the wrong sign for the current hypothesis:

| Factor | Horizon | IC | ICIR | t | FDR | Pos IC | QSpread | Mono | Research Lead |
|---|---:|---:|---:|---:|---|---:|---:|---:|---|
| `pead_event_gap_underreaction_1_20` | 5 | -0.1240 | -0.626 | -3.43 | True | 26.7% | -0.0116 | -1.000 | no |

Interpretation: the pre-registered "gap underreaction" sign is backwards on this sample. It behaves more like a short-horizon post-announcement gap overreaction/reversal diagnostic than a continuation factor.

## Why Nothing Is Promotable

- The only FDR-significant result has negative IC, negative quantile spread, and negative monotonicity under the registered direction.
- No candidate passed the combined industry, size, and liquidity neutral gate.
- ICIR values are weak for the positive-sign candidates.
- Quantile monotonicity is weak or wrong-signed for most rows.
- Portfolio grids, Sharpe, win rate, profit rate, total return, and drawdown remain blocked.

## Gate Decision

Do not continue tuning the original PEAD underreaction/continuation formulas.

Allowed next action:

```text
round223_financial_pit_post_announcement_gap_reversal_preregistration
```

The repair must be pre-registered before any IC or portfolio run. It should test the inverse event-gap mechanism as a new hypothesis, with controls for size/liquidity exposure and the same PIT/event-date alignment rules.

Safety boundary remains research-to-review only: no broker connection, no live account reads, no order placement, and no automatic live trading.
