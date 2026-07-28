# CN ETF Monetization Runway

Date: 2026-07-28

## Current position

The project is at **research-family rotation with an external data blocker**.
It is not at portfolio promotion, paper deployment, or live trading.

No current CN ETF factor has passed the complete preregistered chain of
statistical materiality, independence, capacity, and cost gates. The strongest
new result in this work session had a slightly positive H5 spread after the
frozen 10 bps cost model, but it failed the mandatory IC, ICIR, FDR,
independence, and every-date capacity gates. Calling it a profitable strategy
would be incorrect.

The shortest defensible route forward is historical daily ETF PCF data. The
official Tushare PCF and structured ETF-to-index endpoints require 8,000 points
and are denied to the current local credential. A bounded unaffiliated public
fallback also failed and remains unverified for licensing and completeness.

## Critical path to a paper candidate

| Gate | Work after input arrives | Exit condition |
| --- | --- | --- |
| 1. Source acquisition | Backfill SSE and SZSE PCF for 2020-01-02 through 2024-06-28 | Complete licensed raw history |
| 2. Source readiness | Fingerprint, normalize, align publication time, audit gaps/duplicates/schema | Frozen point-in-time source passes |
| 3. One preregistration | Define one compact PCF/basket-pressure hypothesis and fixed controls | Hash-bound single-run authorization |
| 4. Prescreen | Test H5 primary and H20 diagnostic with closed-family deduplication | Every primary gate passes |
| 5. Validation | Walk-forward, regime, cost, turnover, capacity, and stability review | Reproducible net-positive paper candidate |
| 6. Paper observation | Observe at least the configured 20 days and 30 paper fills | No guardrail breach and enough regimes |
| 7. Manual small-capital review | Apply capped capital and loss policy | Human review packet only; no automatic execution |

Failure at gates 2–5 closes the new family without tuning or holdout rescue.
That is the expected cost of avoiding false profits.

## What the operator should provide

### Blocking now

Provide **one** of:

1. enable the current Tushare account for `etf_sh_cons`, `etf_sz_cons`, and
   preferably `etf_basic`; or
2. place a licensed SSE+SZSE historical PCF export on this computer and provide
   its data dictionary.

For the fastest path, a bulk historical export is preferable to a permission
upgrade alone. The official endpoints cap each response at 3,000 rows, so a
complete multi-year, multi-ETF backfill still requires substantial sharding and
provider calls.

The repository now includes a machine-readable delivery contract at
`configs/cn_etf_pcf_delivery_contract.json` and a review-only validator:

```powershell
python scripts\validate_cn_etf_pcf_delivery.py --input <file> --exchange SSE --provider <provider-name>
```

Run the corresponding command for SZSE separately. The validator fingerprints
the input and checks aliases, key uniqueness, exchange suffixes, nonnegative
quantities, and the frozen date boundary. It writes only a lightweight report;
it does not write canonical market data or authorize factor generation.

The repository now builds the frozen target universe locally from the
all-status Tushare `fund_basic` snapshot and the analysis-window bar authority:

```powershell
python scripts\build_cn_etf_pcf_target_universe.py
```

The current real run cleared with 1,069 ETFs across both exchanges, including
101 delisted funds. The 51 ETF-classified metadata rows with missing list dates
had no bar in the analysis window. The generated target artifact SHA-256 is
`0082e32b1f3704ce19301c871bee62e1cebbded650ab496f413df868e93bad9a`.
Therefore the operator does not need to supply another target-universe file
unless the licensed PCF export uses a materially different scope.

After the PCF delivery arrives, run:

```powershell
python scripts\run_cn_etf_pcf_source_readiness.py `
  --sse-input <sse-file-or-directory> `
  --szse-input <szse-file-or-directory> `
  --target-universe data/processed/cn_etf_pcf_target_universe_2020_2024/target_universe.csv `
  --provider <provider-name>
```

This second gate recursively discovers CSV/Parquet partitions, fingerprints
every source file, validates the official calendar artifact, and requires 100%
ETF-session basket coverage across the frozen delivered scope (with a hard
minimum of 30 ETFs) and both exchanges.
It writes only readiness reports and coverage tables. Even a cleared result
permits preregistration only; factors and returns remain unread.

Also provide authoritative ETF bars for 2020-05-28 and 2020-06-03 if available.
The current bar authority has no rows on those two official sessions.

### Needed before cost and capacity validation

Fill a copy of
`configs/cn_etf_monetization_inputs_template.json` with:

- intended initial research/paper capital;
- maximum single-position size, daily loss, and acceptable drawdown;
- actual ETF commission per side, minimum commission per order, and other
  applicable fees;
- realistic normal and stressed slippage;
- maximum acceptable market participation;
- acceptable holding-period and rebalance-frequency range;
- availability for manual paper review.

Do not put account numbers, broker credentials, API secrets, tokens, or order
authorization in the file.

If these values are not supplied when a factor reaches validation, the project
will continue using conservative defaults. That is safe but can reject a
small-capital idea because minimum order fees and realistic slippage are not
modeled precisely.

## Existing safeguards already available

The repository already contains:

- a default small-capital review ceiling of CNY 10,000;
- a CNY 1,000 maximum single-order notional;
- a CNY 200 maximum daily loss;
- an 8% maximum paper drawdown;
- minimum evidence of 20 observation days, 30 paper fills, and two regimes;
- broker, account, order, and live-boundary prohibitions.

These defaults can remain in force until the operator supplies a different
research policy. They are review constraints, not permission to trade.

## What is not needed now

Do not provide:

- a broker login or trading API;
- live account access;
- an order-placement permission;
- live capital;
- a promise to accept more risk.

Those inputs do not solve the current bottleneck. Historical point-in-time data
and explicit execution economics do.

## Definition of “closer to earning money”

The next meaningful milestone is not a higher backtest return. It is a
preregistered candidate that:

1. survives false-discovery control and closed-family deduplication;
2. remains positive after the operator's actual fee and slippage model;
3. fits the intended capital without violating participation limits;
4. remains stable across years and market regimes;
5. completes paper observation without guardrail breaches.

Only after that evidence exists should a separate human decision consider a
small-capital pilot. The project remains research-to-paper and cannot make a
profit guarantee.
