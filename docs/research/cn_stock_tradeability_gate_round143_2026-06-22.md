# CN Stock Tradeability Gate Round143

Date: 2026-06-22

## Purpose

Round143 implements the first reusable A-share tradeability gate for CN stock factor mining. This is a process improvement, not a factor discovery or promotion result.

The gate addresses the highest-risk issue from the Round142 quality audit: historical factor returns can be dominated by stocks that were not realistically buyable or sellable because of listing age, ST/delisting risk, board permission, zero-volume execution rows, or limit-up/limit-down states.

## What Was Added

- `src/quant_robot/ops/cn_stock_tradeability_gate.py`
- `scripts/run_cn_stock_tradeability_gate.py`
- `tests/unit/test_cn_stock_tradeability_gate.py`
- `tests/unit/test_cn_stock_tradeability_gate_cli.py`
- `docs/superpowers/plans/2026-06-22-round143-cn-stock-tradeability-gate-plan.md`

The module exposes:

- `CNStockTradeabilityPolicy`
- `build_cn_stock_tradeability_frame`
- `build_cn_stock_tradeability_report`
- `render_markdown`
- `write_tradeability_report`

## Implemented Controls

Implemented with local `stock_basic` metadata:

- ST/name-risk exclusion.
- Listing-age exclusion.
- Board permission blocks for BSE, STAR, and ChiNext unless explicitly allowed.

Partial/proxy controls:

- Limit-up/limit-down filter: implemented as an OHLCV close-at-limit proxy.
- Suspension filter: implemented as zero/missing OHLCV or zero amount proxy.
- Delisting risk: blocks inactive or `delist_date` reached rows when metadata has those fields, but the current metadata is a latest snapshot rather than full PIT delist history.

## Sample Local Evidence

Command:

```powershell
python scripts\run_cn_stock_tradeability_gate.py --bars-path <2023-bars-parquet> --stock-basic-path <stock-basic-parquet> --output-dir data\reports\cn_stock_tradeability_gate_round143
```

Sample result on one 2023 office-desktop CN-stock bars shard:

- Rows: 628,167
- Assets: 5,351
- Can-buy rows: 353,429
- Can-sell rows: 356,164
- Fully tradeable rows: 352,677
- Board-permission blocked rows: 249,488
- ST rows: 27,816
- New-listing rows: 13,470
- Limit-up-like rows: 4,739
- Limit-down-like rows: 1,073
- Suspended-proxy rows: 0

Generated artifacts:

- `data/reports/cn_stock_tradeability_gate_round143/cn_stock_tradeability_gate.json`
- `data/reports/cn_stock_tradeability_gate_round143/cn_stock_tradeability_gate.md`

## Quality Gate Impact

Round142 quality-gate classification before this work:

- Implemented controls: 1
- Partial controls: 10
- Planned controls: 21

Round143 classification after this work:

- Implemented controls: 4
- Partial controls: 12
- Planned controls: 16

Interpretation:

- The project now has a reusable tradeability gate that can be applied before future factor screens.
- Promotion is still blocked because proxy-only controls are not equivalent to official exchange/Tushare suspension and limit data.
- Future factor mining should consume this gate before ranking candidates, especially for any factor that tends to select BSE, new-listing, low-turnover, or event-jump tails.

## Verification

Commands run:

```powershell
python -m unittest tests.unit.test_cn_stock_tradeability_gate tests.unit.test_cn_stock_tradeability_gate_cli
python -m json.tool configs\factor_mining_quality_gate_cn_stock.json > $null
python scripts\run_factor_mining_quality_gate.py --config configs\factor_mining_quality_gate_cn_stock.json --output-dir data\reports\factor_mining_quality_gate_round143
```

All commands completed successfully.
