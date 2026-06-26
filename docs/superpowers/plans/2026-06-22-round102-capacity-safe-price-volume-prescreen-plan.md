# Round102 Capacity-Safe Price-Volume Prescreen Plan

## Steps

1. Add failing tests for the prescreen operation and CLI.
2. Implement factor computation, label alignment, IC, quintile, turnover, and multiple-testing summaries.
3. Run synthetic unit tests.
4. Run real 2015-2025 CN stock data.
5. Fix any performance or memory issue with a regression test.
6. Write Round102 report and update startup gate.
7. Run startup gate, unit tests, project audit, and whitespace verification.

## Result

The first real run exposed an all-factor merge memory issue. A regression test was added and the summarizer was changed to stream per factor and per horizon. The full real-data run then completed.

Round102 produced one research lead:

- `bollinger_reversal_lowvol_liquid_20`, horizon 20

No factor was promoted.

