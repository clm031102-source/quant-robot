# CN ETF Market-Residual Volatility Prescreen Closeout

Date: 2026-07-16

Machine: `office_desktop`

Task: `factor_batch`

Branch: `codex/factor-batch-cn-etf-market-residual-volatility-20260716`

Status: rejected with zero research leads; `cn_etf_volatility_regime` stop-lossed

## Executive Decision

The frozen last-chance market-residual volatility prescreen completed all six candidate-horizon tests and produced zero research leads. The volatility-regime family is therefore closed with budget 0 under the preregistered decision rule.

The strongest row, `etf_idio_vol_low_60` at horizon 20, had statistically positive Rank IC but was not a new alpha source: its mean daily cross-sectional rank correlation with the already rejected `low_volatility_60` reference was 0.871466, above the frozen 0.85 duplicate threshold. It also failed the one-percent participation capacity gate. The other five rows failed one or more statistical, directional, yearly-consistency, duplicate, or capacity gates.

No sign inversion, alternate window, threshold relaxation, blend, regime rescue, portfolio grid, or walk-forward run is allowed. The scheduler allocation is now:

- `cn_etf_flow_breadth_aggregation`: 0.35
- `cn_etf_fund_structure`: 0.35
- `cn_etf_peer_relative_value`: 0.30
- `cn_etf_volatility_regime`: 0.00, stop-lossed

The next authorized work is a metadata-readiness review for same-index or tightly defined same-theme ETF peers. The scheduler emits `run_metadata_readiness_review`, not a factor-batch action, for this family.

## Frozen Contract And Provenance

- Config: `configs/cn_etf_market_residual_volatility_prescreen_20260716.json`
- Config SHA-256: `303b0a66961baa65fbbf72f55f0ad030675908b061954017ae84a890dea62ad0`
- Result JSON SHA-256: `736dbf2fd39d6d0c8e0e947ddb1fdde58e919a6732a28221a68a62ecfa51b539`
- Legacy promotion report SHA-256: `0f1e3c0020d455a6262a9b4d9bd617a4107ddb481345df35ee513efcaf12ea81`
- Analysis window: 2020-01-02 through 2024-06-28
- Final holdout boundary: 2026-01-01 and later
- Execution lag: one session
- Multiple testing: Benjamini-Hochberg across all six frozen tests
- Capacity assumption: CNY 1 million portfolio, ten positions, CNY 100,000 per position, maximum one-way participation 1% of ADV20
- Contract enforcement: the CLI rejects any drift in the analysis window, point-in-time eligibility, market proxy, candidate parameters, references, statistical thresholds, capacity assumptions, multiple-testing policy, zero-lead allocation, or research/live boundaries before data loading
- Reference completeness: every frozen historical reference must supply at least the configured minimum number of usable daily cross-sections; present-but-all-null reference rows fail closed rather than being treated as zero correlation

The processed-bar loader now applies year-partition boundaries before opening files. A regression test places an unreadable 2026 partition beside valid historical data and confirms that an analysis ending in 2024 never opens the sealed file. This converts the holdout rule from a post-load filter into a file-access boundary.

## Data Accounting

| Item | Count or range |
| --- | ---: |
| Source rows | 1,119,490 |
| Source assets | 1,781 |
| Source dates | 1,085 |
| Eligible asset-date keys | 227,010 |
| Eligible assets | 679 |
| Eligible dates | 833 |
| Factor rows | 681,030 |
| Reference rows | 2,043,090 |
| Label rows | 2,191,185 |
| Daily IC observations | 4,337 |
| Yearly IC rows | 24 |
| Frozen candidates | 3 |
| Horizons | 2 |
| Tests | 6 |
| Historical references | 9 |
| Research leads | 0 |

Eligibility was point-in-time, official-ETF-only, required 252 prior observations, required trailing median amount of at least CNY 5 million, capped stale-price rate at 5%, and rejected absolute daily returns above 20%.

## Results

| Factor | H | Mean IC | ICIR | FDR q | IC positive | Q5-Q1 | Mono | Turnover | Positive years | Max ref corr | ADV20 P10 | Participation | Lead |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `etf_idio_vol_low_60` | 20 | 0.1007 | 0.445 | 0.0022 | 67.7% | 0.00843 | 0.90 | 4.2% | 100% | 0.8715 | 7,511,849 | 1.33% | no |
| `etf_downside_beta_low_120` | 20 | 0.0873 | 0.259 | 0.0542 | 61.8% | 0.01200 | 1.00 | 5.0% | 75% | 0.6502 | 9,236,339 | 1.08% | no |
| `etf_idio_vol_low_60` | 5 | 0.0554 | 0.237 | 0.0022 | 58.5% | 0.00191 | 0.90 | 4.2% | 100% | 0.8715 | 7,466,570 | 1.34% | no |
| `etf_downside_beta_low_120` | 5 | 0.0373 | 0.102 | 0.1226 | 53.4% | 0.00219 | 0.90 | 5.0% | 50% | 0.6502 | 9,188,983 | 1.09% | no |
| `etf_positive_residual_skew_60` | 5 | -0.0359 | -0.172 | 0.0145 | 43.9% | -0.00107 | -0.90 | 9.5% | 0% | 0.1898 | 8,858,950 | 1.13% | no |
| `etf_positive_residual_skew_60` | 20 | -0.0531 | -0.267 | 0.0542 | 39.1% | -0.00597 | -0.90 | 9.5% | 0% | 0.1898 | 8,871,030 | 1.13% | no |

## Gate Interpretation

### Idiosyncratic volatility

Both horizons passed the FDR and positive-year gates. Horizon 20 also passed the ICIR gate. However, both rows breached the 0.85 duplicate ceiling against `low_volatility_60` and both required more than 1% participation at the top-quantile ADV20 P10. This is useful confirmation that removing the common ETF return did not produce enough independent information. It is not a lead.

### Downside beta

The horizon-20 row was the nearest independent candidate, with reference correlation 0.650174 and positive IC in three of four usable years. It still missed the 0.30 ICIR gate, missed FDR at 5%, and failed capacity. Horizon 5 was weaker on FDR, ICIR, positive-IC frequency, yearly consistency, and capacity. The preregistered rules leave no statistical or capacity rescue.

### Positive residual skew

Both rows had negative IC, negative Q5-Q1 spread, negative monotonicity, and zero positive years. The result is directionally opposite to the registered economic thesis and worsened at horizon 20. Sign flipping after observing the result is prohibited, so this path is closed rather than renamed.

### Capacity

All six rows failed the same capacity boundary. Top-quantile ADV20 P10 ranged from about CNY 7.47 million to CNY 9.24 million, implying 1.08% to 1.34% one-way participation for a CNY 100,000 position. The result is close in some rows but the threshold was frozen, and threshold relaxation is prohibited.

## Legacy Quarantine

The current legacy promotion report contains 45 raw-volatility rows and blocks all 45. Those rows do not carry the current fold and adjusted-IC evidence needed for promotion. They remain rejection history only and cannot be used to override this prescreen or reopen the family.

## Feasibility And Remaining Risks

- The computation and point-in-time construction are feasible and reproducible on the office desktop.
- The available long sample ends on 2024-06-28. A future lead in another family still requires an audited 2024-H2 through 2025 backfill before walk-forward validation.
- The 2026 final holdout stayed sealed and was not opened.
- Current metadata does not establish reliable official same-index groups. Peer-relative work must begin with a mapping coverage, ambiguity, lifecycle, and point-in-time audit.
- Name-only theme classification is not sufficient because it can silently create false peers and hindsight-contaminated groups.
- Zero leads means no portfolio or profitability claim can be made from this batch.

## Next Research Direction

Run a separate `factor_review` task for `cn_etf_peer_relative_value` with this order:

1. Inventory official benchmark/index fields, fund names, lifecycle metadata, NAV fields, share/scale fields, and available theme labels without downloading new data unless a documented gap requires it.
2. Measure same-index and same-theme peer-group coverage by date, group size, ambiguity, stale membership, and survivorship risk.
3. Define a point-in-time mapping hierarchy and reject name-derived groups that fail quality thresholds.
4. Search the repository for duplicate price/NAV, tracking-error, spread, liquidity, and peer-relative formulas.
5. Only if metadata readiness passes, preregister a compact independent prescreen. Do not implement candidates before that review.

## Safety Boundary

Research-to-paper only. No paper signal, broker connection, account read, order placement, automatic live trading, or profitability claim is authorized.
