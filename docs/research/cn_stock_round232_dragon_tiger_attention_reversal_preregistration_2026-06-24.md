# CN Stock Round232 Dragon-Tiger Attention Reversal Preregistration - 2026-06-24

## Scope

Round232 rotates away from the failed Round229-231 block and tests a new CN stock public event-disclosure surface: 龙虎榜 abnormal-trading disclosures.

This is research-only:

- portfolio grid allowed: false;
- promotion allowed: false;
- same-day disclosure trading allowed: false;
- final holdout: not touched;
- broker/account/order/live trading: forbidden.

## Why This Direction

The last three factor rounds failed because raw or neutral IC did not survive residual/exposure gates. Round232 therefore moves to a different information source with a clearer public availability timestamp:

- Tushare `top_list`: daily Dragon-Tiger list rows, documented as historical data from 2005 to present and retrievable by `trade_date`.
- Tushare `top_inst`: Dragon-Tiger institutional seat transaction detail, also retrievable by `trade_date`.

The event is public after close, so the signal date must be the first open trade date after the listed `trade_date`.

## Pre-Registered Factors

| Factor | Endpoint | Direction | Formula Sketch | Rationale |
|---|---|---|---|---|
| `dragon_tiger_abnormal_attention_reversal_1d` | `top_list` | higher is better after reversal encoding | `-abs(pct_change) * amount_rate` | abnormal attention may overreact and reverse after disclosure |
| `dragon_tiger_net_buy_continuation_1d` | `top_list` | higher is better | `net_amount / amount` or `net_rate` | disclosed net buying may proxy short-horizon demand continuation |
| `dragon_tiger_net_sell_exhaustion_reversal_1d` | `top_list` | higher is better after exhaustion encoding | `-net_amount / amount` when net sell is large | forced disclosed selling may exhaust supply |
| `dragon_tiger_institutional_net_buy_pressure_1d` | `top_inst` | higher is better | institutional `net_buy` aggregated by stock/date | institutional seats may be cleaner informed-flow disclosure |
| `dragon_tiger_institutional_disagreement_abs_pressure_1d` | `top_inst` | higher is better | `abs(sum(net_buy))` or buy+sell pressure scaled by amount | absolute institutional pressure may proxy attention/disagreement |

## Candidate Plan Gate

Config:

```text
configs/factor_mining_candidate_plan_round232_dragon_tiger_attention_reversal_20260624.json
```

Gate output:

```text
data/reports/factor_mining_candidate_plan_gate_round232_dragon_tiger_attention_reversal_20260624
```

Gate result:

- status: `research_ready`;
- candidate count: 5;
- active candidates: 5;
- complete control areas: 8 / 8;
- blockers: none;
- research screen allowed: true;
- portfolio grid allowed: false;
- promotion allowed: false.

## Coverage Smoke

Output:

```text
data/reports/round232_dragon_tiger_attention_reversal_20260624/coverage_smoke
```

Sample design:

- quarterly first open trading dates from 2015-01-01 through 2025-12-31;
- plus the documented `20180928` example date;
- total sample dates: 45.

Results:

| Endpoint | Requests | Successful | Non-empty dates | Rows | Errors |
|---|---:|---:|---:|---:|---:|
| `top_list` | 45 | 45 | 45 | 2,904 | 0 |
| `top_inst` | 45 | 45 | 44 | 33,057 | 0 |

This is enough to proceed to a full coverage audit/cache. It is not alpha evidence.

## Required Next Gate

Next direction:

```text
round232_dragon_tiger_full_coverage_audit_before_pit_prescreen
```

The next gate must:

1. Pull or cache `top_list` and `top_inst` by trade date for the available long-cycle window.
2. Build a disclosure availability calendar where `available_date` is strictly after `trade_date`.
3. Aggregate duplicate stock-date-reason rows without losing source-event counts.
4. Join bar context (`amount`, `adv20_amount`, `log_adv20`) and stock_basic industry.
5. Stop if endpoint coverage is sparse, same-day alignment appears, or field coverage is insufficient.
6. Only then run PIT event IC with industry/size neutralization.

## Stop-Loss Rules

- If full-cycle coverage is sparse or permission-limited, do not simulate missing data.
- If the prescreen finds 0 neutral research leads, rotate away instead of tuning reason categories.
- If only same-day or event-day returns explain the signal, reject as event contamination.
- If signal is just size, turnover, limit-up, or industry exposure, reject before portfolio conversion.

## Source Notes

- Tushare `top_list` docs describe 龙虎榜每日明细 with `trade_date`, `ts_code`, `amount`, `l_buy`, `l_sell`, `net_amount`, `net_rate`, `amount_rate`, and `reason`.
- Tushare `top_inst` docs describe 龙虎榜机构成交明细 with `trade_date`, `ts_code`, `side`, `buy`, `sell`, `net_buy`, and `reason`.
- Tushare efficient-pull guidance recommends using `trade_date` for whole-market historical pulls instead of looping thousands of stocks.
