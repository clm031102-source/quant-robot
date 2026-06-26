# CN Stock Rounds234-236 Three-Round Review - 2026-06-25

## Scope

This review covers three work units:

- Round234: Dragon-Tiger hibernation and accounting-quality family rotation.
- Round235: income, balance sheet, and cash-flow statement input implementation plus limited smoke.
- Round236: full-universe statement shard plan plus long-cycle pilot.

This review is research-only. No broker connection, account reads, order placement, or live trading.

## Round Outcomes

| Round | Work | Result | Factor outcome |
|---|---|---|---|
| 234 | Hibernated Dragon-Tiger after zero residual leads; selected accounting-quality data readiness | Cleared family rotation; blocked direct factor generation | 0 new factors |
| 235 | Added Tushare statement mapping/adapter/combined ingest; fixed readiness gate | Limited 2-symbol, 2-period smoke passed; 12 endpoint requests, 4 processed rows, 2 / 2 field groups passed | 0 new factors |
| 236 | Built full-universe shard plan; ran 2-symbol 2015-2025 pilot | Plan passed; pilot passed readiness with 264 endpoint requests, 88 processed rows, 1 empty request | 0 new factors |

## What Improved

The process stopped a bad loop:

- Dragon-Tiger was not tuned further after direct PIT and size-residual failures.
- Accounting quality was not mined from incomplete `fina_indicator` ratio data.
- The readiness gate now distinguishes PIT statement readiness from ROE/ROA profitability-ratio readiness.

The project now has a repeatable data path for public accounting-quality anomalies:

- Tushare `income`, `balancesheet`, and `cashflow` endpoints are mapped.
- A combined `processed/financial_statement_inputs` dataset is written.
- Required field groups are audited by an external readiness command.
- Full-universe backfill is planned by endpoint request budget, not by vague "all data" intent.

## Key Evidence

Round235 limited smoke:

- symbols: 2;
- periods: 2;
- endpoint requests: 12;
- processed rows: 4;
- empty requests: 0;
- required groups passing: 2 / 2.

Round236 full-universe plan:

- included symbols: 5,208;
- excluded BJ symbols: 321;
- periods: 44;
- endpoint count per symbol-period: 3;
- shards: 261;
- symbols per shard: 20;
- total endpoint requests: 687,456;
- max endpoint requests per shard: 3,000;
- stratification strata: 2,180.

Round236 long-cycle pilot:

- symbols: `000066.SZ`, `300029.SZ`;
- periods: 44;
- endpoint requests: 264;
- processed rows: 88;
- empty requests: 1 (`balancesheet:000066.SZ:20220331`);
- ann date range: 2015-04-28 to 2026-04-30;
- report period range: 2015-03-31 to 2025-12-31;
- standalone readiness: passed, 2 / 2 required groups.

## Audit

No profitable factor was found in these three rounds. That is correct and desirable: the work was a prerequisite data/method correction, not an alpha screen.

The previous failure mode was "mine before the data is truly suitable". This review confirms the direction has changed:

- from blind moneyflow/event tuning;
- to a public, economically grounded accounting-quality family;
- with full PIT statement data required before preregistration.

Remaining risks:

- Full-universe statement backfill is large: 687,456 endpoint requests.
- Current `stock_basic` is a latest snapshot and still not a full historical PIT membership source.
- Empty responses must be tracked; the first long-cycle pilot already found one empty balance-sheet request.
- Statement fields must be audited for restatements, duplicate report types, and announcement-date availability before factor labels are built.

## Decision

Continue Round236, but do not pre-register accounting-quality factors yet.

Allowed next work:

1. Execute Round236 backfill in subshards or one shard at a time.
2. Run required-column readiness after each shard.
3. Track empty requests and duplicate statement rows.
4. After enough coverage exists, add a coverage manifest before factor preregistration.

Blocked next work:

- no accounting-quality factor generation from only the smoke/pilot sample;
- no portfolio grid;
- no promotion claim;
- no final holdout access.

The next work unit remains:

```text
round236_accounting_quality_statement_full_universe_shard_backfill_before_preregistration
```

## Verification

Verification completed:

- JSON validation passed for changed configs.
- Startup gate cleared and now points to Round236 full-universe statement backfill.
- 53 statement/readiness/shard-plan tests passed.
- 40 startup gate tests passed.
- `git diff --check` passed.
