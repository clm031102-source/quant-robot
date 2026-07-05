# Project Round503 Main Cleanup And Profit Mining Start

Date: 2026-07-04

Machine: office_desktop

Branches:

- Integrated stable branch: `main`
- New mining branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: user-authorized final cloud branch cleanup, `main` integration, and start of profit-factor mining. This remains research-to-paper only: no broker connection, no live account reads, no order placement, and no automatic live trading.

## Main Integration And Cloud Cleanup

The user explicitly authorized continuing from the office desktop to organize all cloud branches and `main`.

Actions completed:

- Pulled latest `origin/main`.
- Merged `origin/codex/factor-batch-cn-stock-benchmark-relative-20260704`.
- Merged `origin/codex/factor-batch-cn-stock-execution-aware-round465-20260704`.
- Ran merged-main integration checks.
- Pushed `main` to GitHub.
- Ran project-sync cleanup, which removed the two absorbed topic branches locally and remotely.

Verification:

- `scripts/run_checks.py --profile laptop-integration --execute` passed.
- Unit tests: 73 / 73 passed.
- Compile step passed.
- Project audit passed with 2,186 files scanned and no forbidden safety hits.
- `scripts/run_checks.py --profile pre-alpha --execute` returned `status=complete`, `progress_estimate_percent=100`, `factor_mining_allowed=true`, and no blockers.

Post-cleanup state:

- Current stable branch: `main`
- Remote topic branches: none
- Changed paths on stable completion check: none
- Observation sufficiency: 25 observed fills / 20 required
- Completion evidence source: `docs/research/project_round501_completion_evidence_2026-07-04.json`

## Profit-Mining Startup

The new mining branch was created from the clean integrated `main`:

```text
codex/factor-batch-cn-stock-profit-mining-20260704
```

Startup gates:

- Quant PM startup gate passed for `office_desktop` / `factor_batch`.
- Primary research market remains `CN_ETF`.
- CN stock work is scoped as a separate CN stock factor batch, not as the primary ETF research line.
- CN stock factor-mining startup gate cleared after correcting the branch and scope to `market=CN`, `asset_type=stock`.
- CN stock data manifest completed with no blockers.

CN stock data manifest snapshot:

- Bars: 15,930,072 rows, 5,774 symbols
- Moneyflow: 14,702,368 rows, 5,648 symbols
- Date range: 2015-01-05 to 2026-06-15
- Warnings: `extreme_return_rows_present`, `moneyflow_symbol_coverage_below_bars`

## Direct Alpha Factory Block

A direct daily-basic alpha-factory discovery attempt was intentionally stopped by the startup-gate validator:

```text
CN processed-bars alpha factory startup gate round state decision is unsupported
```

Interpretation:

- The current method contract does not allow anonymous direct factor generation from this branch.
- The allowed direction remains `paper_simulation_packaging_or_new_pit_source_not_q20_threshold_tuning`.
- Future direct alpha-factory use should first normalize the round-state decision into the supported enum and confirm it is consistent with the current method contract, or use a newly pre-registered PIT source plan.

## Candidate Plan And Screen

Candidate plan gate:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan configs\factor_mining_candidate_plan_round465_ps_gt10_self_risk_overlay_20260704.json --output-dir data\reports\round503_profit_mining_candidate_plan_gate_20260704
```

Result:

- Status: `research_ready`
- Candidate plan cleared: true
- Active candidates: 1
- Control areas complete: 9 / 9
- Research screen allowed: true
- Portfolio grid allowed: false
- Promotion allowed: false

Fixed self-risk overlay screen:

```powershell
.\.venv\Scripts\python.exe scripts\run_shortlist_self_risk_overlay.py --return-source ps_gt10=data\reports\round462_24h_profit_sprint_q20_tail_attribute_cash_filter_20260627\cash_ps_gt_10_official_template_period_returns.csv --output-dir data\reports\round503_profit_mining_ps_gt10_self_risk_overlay_20260704 --return-column period_return --date-column date --periods-per-year 50.4 --holding-period 20
```

Result:

- Base count: 1
- Candidate count: 9
- Top candidate: `ps_gt10_self_roll21_sum_m2_cash`
- Policy: `roll21_sum_m2_cash`
- Annualized return: 0.08507982577628304
- Overlap-adjusted Sharpe: 0.6969712816692145
- Max drawdown: -0.12458721638476855
- Average self-risk exposure: 0.7049723756906078
- Guard event share: 0.2950276243093923

Baseline:

- Candidate: `ps_gt10`
- Annualized return: 0.07794143577038515
- Overlap-adjusted Sharpe: 0.565430805392886
- Max drawdown: -0.2542482236517434

Decision:

- Profit-factor mining has started under the gated paper-risk-repair lane.
- This does not create a new independent alpha claim.
- Promotion remains disabled.
- The 2026 final holdout remains sealed.
- Do not tune `q20`, `m175`, range-contraction, or `ps_ttm` thresholds.
- Do not retry the analyst `report_rc` source again on 2026-07-04 because the provider already returned the same-day `2_per_day` limit.

## Next Direction

Continue only through one of these allowed paths:

- Resume the Round467 analyst-report-revision PIT source after the provider limit resets, then rerun the frozen PIT prescreen with January and February report roots.
- Or register a genuinely new PIT source candidate plan before generating factors.
- Or continue paper-readiness hardening without treating the result as an independent alpha.
