# CN Stock Round367 - Turnover-Low Mainboard Pre-Rank Replacement

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Why This Round

Round366 found that `replace_drop_turnover_f_low10` wastes selected weight on STAR/ChiNext names that are blocked by the default board-permission policy. Round367 tests whether removing those names before ranking and refilling Top50 improves the strategy.

This is deliberately not an entry-date limit-up/down replacement test. Replacing based on next-day limit status would create look-ahead risk unless modeled as a live order-routing rule. This round only uses static board metadata available before selection.

## Output

`data/reports/round367_24h_profit_sprint_turnover_low_mainboard_prerank_replacement_20260627`

Reusable tool added:

- `src/quant_robot/ops/turnover_low_prerank_replacement.py`
- `scripts/run_turnover_low_prerank_replacement.py`
- `tests/unit/test_turnover_low_prerank_replacement.py`

## Variants

All variants use:

- market: CN stock;
- factor: `turnover_rate_low`;
- Top50;
- hold20;
- rebalance5;
- cost: 5 bps per side, 10 bps round trip;
- quarantine: exclude `CN_XBEI`, daily absolute return > 50%;
- entry-cash proxy for unbuyable names.

| Variant | Candidate Rows After Filter | Entry Allowed | Total | Ann. | Sharpe | Overlap Sharpe | Max DD | Win Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `turnover_low_top50_entry_cash_after` | 393,140 | 78.79% | +107.64% | 4.51% | 0.644 | 0.355 | -35.63% | 41.13% |
| `replace_drop_turnover_f_low10_entry_cash_after` | 353,578 | 77.02% | +144.38% | 5.33% | 0.738 | 0.407 | -36.99% | 41.13% |
| `replace_drop_turnover_f_low10_mainboard_prerank` | 175,442 | 95.75% | +180.65% | 6.86% | 0.704 | 0.384 | -48.95% | 48.60% |

## Diagnosis

The pre-rank mainboard filter fixes the operational defect:

- entry allowed rate improves from 77.02% to 95.75%;
- total return improves from +144.38% to +180.65%;
- annualized return improves from 5.33% to 6.86%.

But it also changes the risk profile:

- max drawdown worsens from -36.99% to -48.95%;
- overlap-adjusted Sharpe falls from 0.407 to 0.384.

The likely explanation is that cashing blocked STAR/ChiNext/UNKNOWN positions was unintentionally defensive. Replacing them with more mainboard low-turnover stocks raises exposure and return, but also raises crash/regime risk.

## Decision

`replace_drop_turnover_f_low10_mainboard_prerank` is not promoted.

It is retained only as a high-return research lead that requires an independent risk wrapper. The next round must test block dependence, OOS splits, and vol-target wrappers before considering it for any shortlist.
