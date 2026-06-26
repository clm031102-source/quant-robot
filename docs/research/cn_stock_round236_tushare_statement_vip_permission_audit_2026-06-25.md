# CN Stock Round236 Tushare Statement VIP Permission Audit - 2026-06-25

## Scope

Round236 tested whether Tushare financial statement VIP endpoints can replace the ordinary per-symbol statement backfill path.

This was a permission and efficiency audit only. No factor was generated and no portfolio result was claimed.

## Why This Matters

Tushare statement docs describe both ordinary single-symbol historical endpoints and VIP quarter-wide endpoints:

- `income` / `income_vip`
- `balancesheet` / `balancesheet_vip`
- `cashflow` / `cashflow_vip`

If the VIP endpoints were available, the 2015Q1-2025Q4 full-universe statement backfill could drop from roughly 687,456 endpoint requests to about 132 endpoint requests: 44 quarters times 3 endpoints.

## Live Smoke

Test period:

```text
20240331
```

Fields tested:

- `income_vip`: `ts_code`, `ann_date`, `end_date`, `report_type`, `comp_type`, `end_type`, `n_income_attr_p`, `n_income`, `total_revenue`, `revenue`, `total_cogs`, `operate_profit`, `total_profit`, `income_tax`
- `balancesheet_vip`: `ts_code`, `ann_date`, `end_date`, `report_type`, `comp_type`, `end_type`, `total_assets`, `total_liab`, `total_cur_assets`, `total_cur_liab`, `total_hldr_eqy_exc_min_int`, `total_hldr_eqy_inc_min_int`, `total_liab_hldr_eqy`, `inventories`, `accounts_receiv`, `accounts_pay`
- `cashflow_vip`: `ts_code`, `ann_date`, `end_date`, `report_type`, `comp_type`, `end_type`, `net_profit`, `n_cashflow_act`, `free_cashflow`, `c_cash_equ_end_period`, `c_cash_equ_beg_period`

Result:

| Endpoint | Status |
|---|---|
| `income_vip` | blocked: no interface permission |
| `balancesheet_vip` | blocked: no interface permission |
| `cashflow_vip` | blocked: no interface permission |

## Decision

VIP statement backfill is not currently available for this token. Continue with the ordinary per-symbol statement endpoints, using strict shard/subshard budgeting and resume.

Do not spend more runtime trying VIP endpoints unless the Tushare permission level changes.

## Next Action

Build and use a Round236 shard/subshard execution entrypoint so each ordinary-endpoint backfill segment records:

- source plan;
- shard id;
- symbol offset and count;
- expected endpoint requests;
- actual processed rows;
- empty requests;
- required-column readiness.
