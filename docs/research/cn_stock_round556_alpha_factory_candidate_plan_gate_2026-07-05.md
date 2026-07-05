# CN Stock Round556 Alpha Factory Candidate-Plan Gate

Date: 2026-07-05

Machine context: office desktop as the main work machine

Branch: `codex/factor-batch-cn-stock-round555-20260705`

Scope: harden `scripts\run_tushare_alpha_factory.py` so CN processed-bars factor generation cannot run unless a cleared candidate-plan gate packet matches the actual factor names executed by the alpha factory.

## Change

The CN processed-bars alpha factory now requires three packets before loading bars:

- Cleared startup gate packet.
- Usable CN stock data manifest packet.
- Cleared candidate-plan gate packet.

The candidate-plan validation checks the active preregistered `candidate_rows.factor_name` set against the factor names implied by `--factor-source`.

Supported mappings:

| Factor source | Expected factor names |
| --- | ---: |
| `tushare_daily_basic` | 12 |
| `tushare_moneyflow` | existing moneyflow constant set |
| `moneyflow_technical_combo` | existing moneyflow-technical combo constant set |

If a gate packet is missing or the factor names drift, the script exits before `load_research_bars`.

## Test-First Evidence

Red tests:

- Missing candidate-plan gate did not raise `ValueError`.
- Factor-name drift test errored because `candidate_plan_gate_packet` was not yet accepted.

Green tests:

- `test_processed_cn_alpha_factory_requires_candidate_plan_gate_packet_after_data_manifest`
- `test_processed_cn_alpha_factory_rejects_candidate_plan_factor_name_drift`
- `test_processed_cn_alpha_factory_accepts_cleared_startup_gate_packet`

Additional checks:

- `tests.unit.test_tushare_alpha_factory_cli` and `tests.unit.test_alpha_factory`: 20 tests passed.
- `tests.unit.test_factor_mining_candidate_plan_gate`: 13 tests passed.
- Python compile passed for `scripts\run_tushare_alpha_factory.py` and `src\quant_robot\ops\factor_mining_candidate_plan_gate.py`.

## Real Smoke

Ran a short local processed-bars smoke with the Round555 candidate-plan gate packet:

```powershell
python scripts\run_tushare_alpha_factory.py --source processed-bars --data-root data\processed\office_desktop_20260616_combined_research --market CN --factor-source tushare_daily_basic --factor-input-root data\processed\office_desktop_20260617_daily_basic_factor_inputs\processed\factor_inputs --output-dir data\reports\round556_tushare_daily_basic_candidate_plan_enforced_smoke_20260705 --start-date 2024-01-02 --end-date 2024-01-05 --candidate-plan-gate-packet data\reports\round555_daily_basic_source_smoke_candidate_plan_gate_20260705\factor_mining_candidate_plan_gate.json --allow-review-required-data-manifest
```

Result:

| Metric | Value |
| --- | ---: |
| Hypotheses | 12 |
| Completed | 12 |
| Failed | 0 |
| Adjusted-significant IC screens | 0 |
| Alpha-factory internal paper-eligible rows | 0 |

Interpretation:

- The new gate works on the real local processed-bars path.
- The short two-observation smoke is only execution-path evidence.
- No candidate is promoted and no final holdout was used for tuning.

## Decision

Keep alpha-factory runs fail-closed behind startup, data-manifest, and candidate-plan packets. The next longer discovery-window run should pass `--candidate-plan-gate-packet` explicitly and should remain research-only until long-cycle replay, capacity, regime, and style-neutral gates pass.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- No provider download was used for the smoke.
- No generated `data/reports` artifact is committed.
