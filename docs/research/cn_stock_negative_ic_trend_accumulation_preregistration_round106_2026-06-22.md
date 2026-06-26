# CN Stock Negative-IC Trend Accumulation Preregistration Round106

## Command

```powershell
python scripts\run_negative_ic_trend_accumulation_preregistration.py --output-dir data\reports\negative_ic_trend_accumulation_preregistration_round106_20260622 --min-candidates 8
```

## Source Evidence

- Source audit: `docs/research/cn_stock_capacity_safe_trend_accumulation_prescreen_round105_2026-06-22.md`
- Source round: `round105_capacity_safe_trend_accumulation_prescreen`
- Evidence status: Round105 negative IC is hypothesis evidence, not promotion evidence.
- Observed shape: 20 of 20 factor-horizon tests were FDR-significant with negative mean IC and zero research leads.

## Headline Result

- Stage: `negative_ic_trend_accumulation_preregistration`
- Candidates: 10
- Unique candidate names: 10
- Portfolio backtest allowed candidates: 0
- Promotion allowed candidates: 0
- Blockers: none
- Next required gate: `alphalens_style_ic_quantile_turnover_prescreen`
- Next direction: `round107_negative_ic_trend_accumulation_prescreen`

## Candidates

| Candidate | Family | Windows | Interpretation |
|---|---|---:|---|
| `anti_volume_weighted_momentum_quality_20` | anti-overheat volume-weighted trend | 20 | Avoid late-stage volume-weighted trend while retaining liquidity. |
| `anti_money_pressure_efficiency_20` | anti-overheat money pressure | 20 | Test whether high directional money pressure marks crowding. |
| `anti_accumulation_distribution_pressure_20` | anti-overheat accumulation/distribution | 20 | Treat intense accumulation plus momentum as possible overheat. |
| `anti_turnover_expansion_momentum_10_40` | anti-overheat turnover expansion | 10,20,40 | Test non-crowded momentum versus active-demand spikes. |
| `anti_amount_accumulation_breakout_20_60` | anti-overheat breakout | 20,60 | Treat amount-confirmed breakouts as possible late-stage demand. |
| `anti_obv_late_accumulation_20` | anti-overheat OBV | 20 | Avoid late OBV accumulation before portfolio proof. |
| `overheat_avoidance_high_volume_breakout_20` | overheat-avoidance breakout quality | 20 | Test avoidance of hot breakouts with unusual amount. |
| `overheat_avoidance_relative_strength_60` | overheat-avoidance relative strength | 20,60 | Avoid crowded long relative strength. |
| `amount_exhaustion_pullback_20_60` | amount exhaustion | 20,60 | Prefer liquid names without recent amount breakout pressure. |
| `overheat_avoidance_composite_20_60` | overheat-avoidance composite | 20,60 | Compact composite of the shared Round105 negative-IC cluster. |

## Audit Judgment

Round106 is a clean preregistration step, not a discovery claim. It makes the Round105 lesson actionable while preventing the classic post-hoc inversion trap. The next efficient action is to compute these ten candidates with the same 2015-2025 long-cycle IC, quantile, turnover, FDR, and capacity prescreen used in Round102 and Round105.

No candidate is paper-ready. No candidate may enter a top-N portfolio grid before Round107 prescreen creates a statistical lead.
