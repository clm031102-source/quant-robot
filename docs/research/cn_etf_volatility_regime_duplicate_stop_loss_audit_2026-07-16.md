# CN ETF Volatility-Regime Duplicate And Stop-Loss Audit

Date: 2026-07-16

Machine: `office_desktop`

Task: `factor_review`

Branch: `codex/factor-review-cn-etf-volatility-regime-20260716`

Status: narrowed to one final market-residual prescreen; all previously tested subfamilies closed

Outcome note: the subsequent frozen prescreen completed with zero research leads. The family is now stop-lossed; see `docs/research/cn_etf_market_residual_volatility_prescreen_2026-07-16.md`.

## Decision

Do not repeat raw volatility, low-volatility, downside-volatility, drawdown, recovery, range-contraction, hard-regime, or state-adaptive CN ETF factors. Those structures have already been tested and rejected, or are rank-equivalent derivatives of rejected structures.

The family is not stop-lossed yet because one materially different CN ETF subspace remains untested: volatility and tail shape after removing the point-in-time ETF market component. The only allowed continuation is a frozen three-candidate cross-sectional prescreen:

- `etf_idio_vol_low_60`
- `etf_downside_beta_low_120`
- `etf_positive_residual_skew_60`

This is the last allowed batch for `cn_etf_volatility_regime`. It cannot be expanded with alternate signs, windows, thresholds, blends, regime filters, portfolio grids, or walk-forward runs after results are observed.

## Formula-Level Inventory

| Closed structure | Tested representatives | Evidence | Decision |
| --- | --- | --- | --- |
| Raw realized volatility | `volatility_5/10/20/60/120` | The current strict legacy gate blocks all 45 volatility cases; the older rows have no current fold or adjusted-IC evidence. The full-history seed also rejected `volatility_60`. | Closed; old promotion labels quarantined. |
| Standalone low volatility | `low_volatility_20`, `low_volatility_60` | Round37 rejected 48/48 low-vol/high-liquidity cases. Every low-vol case had negative Sharpe; best low-vol row had Sharpe -0.0399 and adjusted IC p-value 1.0. | Closed as alpha; may remain a diagnostic reference. |
| Downside volatility | `low_downside_volatility_60` | Defensive seed rejected it with weak aggregate Sharpe and adjusted IC p-value 1.0. | Closed. |
| Drawdown resilience | `drawdown_resilience_60` | Full-history diagnostic had 0 accepted folds and adjusted IC p-value 1.0 despite shallow drawdown. | Closed. |
| Defensive blends | `defensive_reversal_60`, `trend_resilience_60`, `risk_confirmed_momentum_60` | Full-history and mature-window diagnostics rejected every blend; mature-window `defensive_reversal_60` Sharpe was -4.5771. | Closed; no weight rescue. |
| Crash/recovery asymmetry | `crash_recovery_60`, `recovery_quality_60`, liquid variants | Repeated diagnostics produced at most one accepted fold, adjusted IC p-value 1.0, and capacity warnings. | Closed. |
| State-adaptive defense | `state_adaptive_trend_defense_60`, `state_stress_defensive_resilience_60`, `state_stress_recovery_leadership_60` | All three rejected with 0 accepted folds and adjusted IC p-value 1.0; stress-only rows were underpowered. | Closed. |
| Hard market-regime deletion | positive benchmark momentum over 5-252 sessions | Round38 preflight found median allowed dates below policy; longer lookbacks created zero-allowed folds. | Closed on the 2020-2024 sample. |
| Volatility/range compression | `formula_range_contraction_breakout_20` and liquid/low-vol variants | Short-window Sharpe cluster collapsed to 0.44-0.53 in full-sample replay, all candidates were capacity-blocked, and long-cycle coverage was insufficient. Tie-breakers reduced performance. | Frozen weak historical lead only; no further tuning. |
| Public volatility-normalized indicators | Bollinger, SuperTrend/ATR, Donchian and capacity repairs | Round44-45 produced no accepted candidate; capacity cleaning removed the apparent return edge. | Closed as primary alpha families. |

## Evidence Quality

The historical evidence is not equally strong, so this audit separates it into three levels.

### Current strict evidence

- The canonical promotion report contains 270 candidates, 270 blocked, and 0 paper-ready.
- Its 45 raw-volatility rows are all blocked and lack current walk-forward fold and adjusted-IC fields. They are useful rejection history, not reusable promotion evidence.
- The point-in-time source available on this machine contains 1,119,490 CN ETF rows from 2020-01-02 through 2024-06-28. The later 2026 observations remain a sealed final holdout.

### Qualified historical diagnostics

- Round37 used 264 liquid ETFs, 1,085 dates, four folds, execution lag 1, 5/10 bps costs, and a cleared ETF preflight. All 48 cases were rejected.
- Round38 blocked hard-regime filtering before walk-forward because evidence coverage was too sparse.
- Round41 showed that liquidity and low-volatility tie-breakers did not improve the range-contraction base.
- Round42 full-sample replay materially reduced the short-window Sharpe and exposed extreme participation rates.

### Historical-only diagnostics

The 2026-06-17 high-spec desktop report used a broader local dataset that is not present on this office machine and predates the current final-holdout policy. Its repeated rejection of raw volatility, defensive, recovery, and state-adaptive structures is valid duplicate/stop-loss evidence, but it is not sufficient for promotion today.

## Remaining Untested Subspace

Repository search found no CN ETF config, report, or factor implementation for idiosyncratic volatility, downside beta, or residual skew. Similar machinery exists for CN stocks, where market-residual candidates were prescreened in Round110-112. That stock evidence is a public-method translation and implementation reference only; it does not establish an ETF result.

The remaining ETF test changes the information source rather than a parameter:

1. Build a point-in-time ETF market return from the median return of ETFs eligible on each signal date.
2. Estimate rolling market beta and downside beta from signal-date and earlier observations.
3. Evaluate residual volatility and residual skew after the common ETF market component is removed.
4. Reject any candidate whose mean daily cross-sectional correlation with an already tested volatility/drawdown/compression reference is at least 0.85 in absolute value.

The exact formulas and gates are frozen in `docs/superpowers/specs/2026-07-16-cn-etf-market-residual-volatility-prescreen-design.md` and `configs/cn_etf_market_residual_volatility_prescreen_20260716.json`.

## Zero-Lead Stop-Loss

If all six factor-horizon rows fail, immediately:

1. Set `cn_etf_volatility_regime` to `stop_lossed` with budget 0.
2. Prohibit sign inversion, window tuning, threshold relaxation, regime rescue, portfolio grids, and walk-forward runs for the family.
3. Keep `cn_etf_flow_breadth_aggregation` at 0.35.
4. Raise `cn_etf_fund_structure` from 0.30 to the 0.35 family cap.
5. Activate `cn_etf_peer_relative_value` at 0.30 as the third independent primary family.

The replacement family is distinct from single-fund structure: it must test same-theme or same-index ETF peer dislocations, tracking-efficiency differences, or price/NAV relative value, subject to a separate metadata-readiness review and preregistration.

## Data Gaps And Limits

- The current long sample ends on 2024-06-28; 2024-H2 through 2025 is absent.
- The 2026 final holdout must remain sealed.
- The local official fund metadata supports lifecycle and broad fund type, but does not provide a reliable official same-index mapping. Peer-relative research therefore needs a separate mapping-quality gate.
- A prescreen lead would authorize only a data backfill and validation design. It would not establish a profitable or deployable factor.

## Sources

- `docs/research/highspec_desktop_cn_etf_rotation_seed_2026-06-17.md`
- `docs/research/cn_etf_liquid_defensive_lowvol_liquidity_round37_2026-06-21.md`
- `docs/research/cn_etf_rounds37_39_audit_2026-06-21.md`
- `docs/research/cn_etf_liquid_range_contraction_risk_overlay_round38_2026-06-21.md`
- `docs/research/cn_etf_liquid_range_contraction_composite_round41_2026-06-21.md`
- `docs/research/cn_etf_range_contraction_long_cycle_replay_round42_2026-06-21.md`
- `docs/research/cn_etf_public_indicator_full_sample_round44_2026-06-21.md`
- `docs/research/cn_etf_cn_stock_rounds44_46_audit_2026-06-21.md`
- `docs/research/cn_stock_market_residual_risk_premia_prescreen_round111_2026-06-22.md`

## Safety

Research-to-paper only. No paper signal, broker connection, account read, order placement, automatic live trading, or profitability claim is authorized.
