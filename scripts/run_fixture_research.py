from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.research.pipeline import ResearchPipelineConfig, run_research_pipeline


def run_fixture_research(output_dir: Path | str = Path("data/reports/fixture_research")) -> dict[str, object]:
    output_path = Path(output_dir)
    bars = load_demo_market_bars()
    result = run_research_pipeline(
        bars,
        ResearchPipelineConfig(
            factor_name="momentum_2",
            factor_windows=(2, 3),
            market="ALL",
            top_n=2,
            cost_bps=5.0,
            output_dir=output_path,
        ),
    )
    return {
        "market_count": int(bars["market"].nunique()),
        "bar_rows": int(len(bars)),
        "factor_rows": int(result["artifact_rows"]["factors"]),
        "label_rows": int(result["artifact_rows"]["labels"]),
        "ic_rows": int(result["artifact_rows"]["ic"]),
        "metrics": result["metrics"],
    }


def main() -> None:
    result = run_fixture_research()
    print(json.dumps(result["metrics"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
