# CN Stock Round390 - Trade Group Contribution Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Purpose

Round390 audited where the frozen primary low-turnover repair template earns its selected-trade contribution.

This is not a new factor. It is an exposure and concentration audit meant to answer whether the current return stream is secretly a single industry, board, exchange, or HS-eligibility bet.

## New Tooling

- `src/quant_robot/ops/shortlist_trade_group_contribution.py`
- `scripts/run_shortlist_trade_group_contribution.py`
- `tests/unit/test_shortlist_trade_group_contribution.py`

The reusable tool summarizes selected-trade contribution by arbitrary trade attributes and writes:

- `group_contribution_summary.csv`
- `group_contribution_top_rows.csv`
- `group_contribution_by_year.csv`
- `trade_group_contribution_audit.json`

## Output

`data/reports/round390_24h_profit_sprint_trade_group_contribution_audit_20260627`

Input trade stream:

`data/reports/round338_24h_profit_sprint_turnover_low_replacement_filters_quarantine_corrected_20260627/replace_drop_turnover_f_low10_trades_with_tradeability.parquet`

Contribution column:

`entry_cash_proxy_weighted_return`

## Result

Overall selected-trade contribution audited: `0.9482`.

| Group Column | Groups | Best Group | Worst Group | Top5 Net Contribution | Top5 Net Share | Top10 Gross Share |
|---|---:|---|---|---:|---:|---:|
| `industry` | 97 | 汽车配件 | 工程机械 | 0.2969 | 31.31% | 38.51% |
| `stock_market` | 4 | 主板 | 科创板 | 0.9482 | 100.00% | 100.00% |
| `exchange` | 3 | XSHG | MISSING | 0.9482 | 100.00% | 100.00% |
| `is_hs` | 4 | H | MISSING | 0.9482 | 100.00% | 100.00% |

Top positive industries by net contribution:

| Industry | Trades | Contribution | Share |
|---|---:|---:|---:|
| 汽车配件 | 1,016 | 0.1041 | 10.98% |
| 超市连锁 | 152 | 0.0596 | 6.29% |
| 建筑工程 | 1,416 | 0.0485 | 5.12% |
| 电气设备 | 679 | 0.0431 | 4.54% |
| 供气供热 | 572 | 0.0415 | 4.38% |

Top negative industries by net contribution:

| Industry | Trades | Contribution | Share |
|---|---:|---:|---:|
| 工程机械 | 167 | -0.0129 | -1.36% |
| 小金属 | 90 | -0.0117 | -1.23% |
| 红黄酒 | 127 | -0.0098 | -1.03% |
| 其他商业 | 45 | -0.0089 | -0.94% |
| 普钢 | 268 | -0.0071 | -0.75% |

## Interpretation

The industry result does not justify a hard industry exclusion:

- the best single industry contributes 10.98% of total contribution, not a single-bucket dependency;
- the top five industries contribute 31.31%, which is meaningful but not extreme;
- the top ten gross contribution share is 38.51%, so activity is spread across many industries;
- negative industries are small in absolute net impact and can easily be noise or regime-specific.

The board result agrees with Round389: STAR and ChiNext do not carry the current template's matched contribution, but excluding structural buckets does not create a better strategy. The current stream is effectively a mainboard/northbound-eligible engine, and blunt board filters are not an alpha source.

## Decision

Do not add any industry, board, exchange, or HS bucket as a new factor.

Use this audit as risk-control evidence:

- industry caps should be tested as exposure/risk-budget rules, not as hard deletions;
- any future industry filter must pass by-year contribution stability and OOS checks;
- if a future candidate earns most of its return from one industry or one year, block simulation promotion.

## Process Lesson

Industry and structural metadata are better used to prevent hidden concentration than to mine new single-bucket alpha. The next useful implementation is an industry-aware risk-budget/cap test around the existing high-return lanes, not another one-off industry exclusion.
