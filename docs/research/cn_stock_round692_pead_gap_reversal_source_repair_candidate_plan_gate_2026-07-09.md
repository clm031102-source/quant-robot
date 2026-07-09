# CN Stock Round692 PEAD Gap Reversal Source Repair Candidate Plan Gate

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-pead-gap-reversal-source-repair-round692-20260709`

Scope: preregister a PEAD gap-overreaction reversal source-repair audit using the expanded Round690 PIT statement source. This round only created the candidate plan and ran the candidate plan gate. It did not run IC screens, residual prescreens, portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, live-trading work, or 2026 final-holdout reads.

## Startup Evidence

| Check | Result |
| --- | --- |
| Machine / task | `office_desktop` / `factor_batch` |
| Quant PM startup gate | `ready`, blockers `[]` |
| Factor mining startup gate | `cleared`, blockers `[]` |
| Startup constraint | `no_gap_reversal_grid_expansion_after_round225_zero_accepted_walk_forward` |
| CN stock data manifest | `review_required`, blockers `[]` |
| Manifest warnings | `extreme_return_rows_present`, `moneyflow_symbol_coverage_below_bars` |
| Live boundary | no broker connection, account reads, orders, or automatic trading |

The manifest warnings are carried forward as prescreen audit inputs. They are not alpha evidence and do not authorize result interpretation without later data-quality notes.

## Candidate Plan

Config:

```text
configs/factor_mining_candidate_plan_round692_pead_gap_reversal_source_repair_20260709.json
```

The plan declares all nine default CN stock control areas:

- `cn_stock_tradeability`
- `financial_pit_timing`
- `source_sample_integrity`
- `industry_style_neutralization`
- `etf_rotation_scope_boundary`
- `portfolio_construction`
- `strict_statistics`
- `china_market_regime`
- `event_factors`

Promotion policy keeps:

```text
promotion_allowed=false
portfolio_backtest_allowed_before_prescreen=false
final_holdout_available_for_tuning=false
```

The plan also blocks PEAD gap-reversal grid expansion after Round225 accepted zero walk-forward portfolio cases. Round692 is limited to source repair on the expanded statement cache.

## Prior Evidence Used

| Round | Evidence |
| --- | --- |
| Round223 | PEAD gap-overreaction reversal produced five residual IC research leads; best 5D IC was about 0.138. |
| Round224 | Dedup froze three highly correlated candidate representatives. |
| Round225 | Walk-forward portfolio preflight accepted zero cases due to capacity, drawdown, and early-cycle stability failures. |
| Round690 | Expanded PIT statement source cleared the source gate with 1,002 symbols and 212,387 rows. |
| Round691 | Financial reporting timeliness produced zero FDR or neutral-gate leads on the expanded source. |

## Preregistered Candidates

| Candidate | Intent |
| --- | --- |
| `stmt_pead_gap_overreaction_reversal_1_5` | Base 5D negative event-gap reversal replayed on expanded statement coverage |
| `stmt_pead_gap_overreaction_reversal_low_liquidity_penalized_1_5` | Round223 best-shape variant with volume-surprise penalty |
| `stmt_pead_gap_overreaction_reversal_volume_confirmed_1_5` | High-attention event-gap reversal check |
| `stmt_pead_gap_overreaction_reversal_size_neutral_candidate_1_5` | Event-gap reversal with explicit event-amount dampening |
| `stmt_pead_gap_overreaction_reversal_quality_conditioned_1_5` | Event-gap reversal with a small PIT-safe fundamental quality condition |

All candidates are `market=CN`, `asset_type=stock`, `registration_status=pre_registered`, `portfolio_backtest_allowed=false`, and `promotion_allowed=false`.

## Candidate Plan Gate Result

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan configs\factor_mining_candidate_plan_round692_pead_gap_reversal_source_repair_20260709.json --output-dir data\reports\round692_pead_gap_reversal_source_repair_candidate_plan_gate_20260709
```

Result:

| Metric | Value |
| --- | ---: |
| Status | `research_ready` |
| Candidate plan gate cleared | true |
| Research screen allowed | true |
| Candidate count | 5 |
| Active candidate count | 5 |
| Complete control areas | 9 / 9 |
| Blocked control areas | 0 |
| Portfolio grid allowed | false |
| Promotion allowed | false |
| Blockers | `[]` |

Ignored generated evidence check:

```text
.gitignore:15:data/reports/ data\reports\round692_pead_gap_reversal_source_repair_candidate_plan_gate_20260709\factor_mining_candidate_plan_gate.json
```

## Decision

Round692 clears the preregistered candidate-plan gate for `pead_gap_reversal_statement_source_repair`. The next allowed action is a statement-source adapter or residual prescreen path that proves `signal_date > ann_date`, excludes the 2026 final holdout, carries manifest warnings, and uses only the five preregistered 5D candidates.

Portfolio grids, promotion, formula-grid expansion, sign/window tuning, mixed-window harvesting, live trading work, and 2026 final-holdout reads remain blocked.
