# Phase 5.14 Paper Ops Guardrail

Phase 5.14 turns the paper-observation history ledger into an operations guardrail.

It does not download market data, connect to a broker, read accounts, place orders, or approve live trading. It only reads the Phase 5.13 history pack and decides whether paper observation may continue, whether the state is watch-only, and whether the evidence is anywhere near a future manual live-readiness review.

## Command

```powershell
python scripts\run_paper_ops_guardrail.py --paper-observation-history data\reports\paper_observation_history\paper_observation_history_pack.json --output-dir data\reports\paper_ops_guardrail
```

Outputs:

- `data/reports/paper_ops_guardrail/paper_ops_guardrail_pack.json`
- `data/reports/paper_ops_guardrail/paper_ops_guardrail_pack.md`
- `data/reports/paper_ops_guardrail/paper_ops_guardrail_checks.csv`
- `data/reports/paper_ops_guardrail/paper_ops_guardrail_next_actions.csv`

## Current Result

- stage: `phase_5_14_paper_ops_guardrail`
- status: `paper_ops_watch`
- continued paper observation allowed: `true`
- live readiness candidate: `false`
- ready runs: `1 / 20`
- ready run deficit for live-readiness review: `19`
- latest provider missing date rows: `226`
- warnings: `short_paper_history`, `provider_missing_date_rows`
- blockers: none
- live boundary violations: `0`
- live boundary allowed: `false`

## Decision Logic

The guardrail has three states:

- `paper_ops_blocked`: history is not clear, latest blockers remain, or any live-boundary violation is present.
- `paper_ops_watch`: paper observation may continue, but the evidence is not mature enough for live-readiness discussion.
- `paper_ops_ready`: paper observation is clear and warning-free under the configured thresholds.

The default live-readiness evidence threshold is `20` paper-ready observations. Provider-level missing rows are warnings by default, even when the current required asset is clean.

## Safety Boundary

This remains research-to-paper only:

- broker connection: disabled
- account reads: disabled
- order placement: disabled
- live boundary: disabled

Passing or watching this phase only controls continued paper observation. It is not permission to trade live.
