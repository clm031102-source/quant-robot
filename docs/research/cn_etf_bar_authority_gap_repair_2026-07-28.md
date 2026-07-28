# CN ETF Bar Authority Gap Repair

Date: 2026-07-28

## Decision

The two whole-market CN ETF bar-authority gaps on 2020-05-28 and 2020-06-03
are repaired and independently reproducible from Tushare `fund_daily`.

This removes the bar-gap promotion blocker for future preregistered research.
It does not reopen any rejected factor family and does not authorize factor
generation, forward-return reads, portfolio tests, paper signals, or live use.

## Repair evidence

The same provider endpoint that returned empty responses during the earlier
backfill now returned:

- 767 rows for 2020-05-28;
- 793 rows for 2020-06-03.

The repair runner wrote fingerprinted raw date partitions, normalized the rows
through the existing CN ETF ingest contract, atomically merged them into the
2020 processed partition, updated the ingest manifest, and rebuilt the
full-2020 quality report.

Result:

- 1,560 rows inserted;
- 2020 rows increased from 191,775 to 193,335;
- 2020 missing asset-date rows decreased from 22,540 to 20,980;
- full authority increased to 1,121,050 rows and 1,087 observed sessions;
- duplicate authority keys remain zero;
- zero-volume rows remain zero.

Fingerprints:

- 2020 partition before:
  `118ee017615656f5c076fe55639acd34d5be00be13e32c07311b536150a61d5c`
- 2020 partition after:
  `892fd8e59621cf9ea0963439c60e6de1c233fcdc251aff7c9b143d76a8498f5e`
- rebuilt quality report:
  `f3f08fa60be888d63cce5069d32ab12d732063309285e690328de2d8cb7f0421`

An immediate cache-only rerun returned `already_repaired`, preserved both
hashes, and made no additional insertions.

## Reproducibility

```powershell
python scripts\repair_cn_etf_bar_authority_gaps.py
```

The command is non-mutating by default. On a still-gapped authority, add
`--execute`. Detailed generated evidence remains under
`data/reports/cn_etf_bar_authority_gap_repair_20260728/`.

## Boundary

The repair changed only research data authority and ignored reports. No
forward return, factor matrix, portfolio result, final holdout, broker,
account, order, paper signal, or live-trading boundary was accessed.
