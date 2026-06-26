# Round98 Profitability Quality Controlled IC Screen Plan - 2026-06-22

## Steps

1. Add tests for controlled IC calculation, multiple-testing flags, CLI behavior, and no-promotion policy.
2. Implement the controlled IC screen as a reusable operation and script.
3. Run unit tests for the operation and CLI.
4. Execute the screen on the Round95 clean 100-symbol shard with the Round96 pre-registered candidates.
5. Inspect top IC results and multiple-testing decisions.
6. Record the result in research documentation and startup gate configuration.
7. Run the project verification commands before reporting completion.

## Stop Conditions

- Stop if label alignment fails.
- Stop if minimum cross-section requirements cannot be met.
- Stop if multiple-testing accounting is missing.
- Stop if any output attempts to mark the factors as promotable without robustness evidence.

## Decision Rule

No research lead means the next round must be a family rejection and rotation audit, not more parameter tuning in the same profitability-quality family.
