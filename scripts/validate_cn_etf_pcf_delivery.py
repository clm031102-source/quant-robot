from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

import pandas as pd  # noqa: E402

from quant_robot.ops.cn_etf_pcf_delivery import (  # noqa: E402
    CANONICAL_COLUMNS,
    audit_cn_etf_pcf_delivery,
    normalize_cn_etf_pcf_delivery,
)
from quant_robot.storage.fingerprints import sha256_file  # noqa: E402


def validate_cn_etf_pcf_delivery(
    input_path: str | Path,
    *,
    market_exchange: str,
    source_provider: str,
    analysis_start: str,
    analysis_end: str,
    output_dir: str | Path,
) -> dict[str, Any]:
    source = Path(input_path)
    frame = _read_delivery(source)
    canonical = normalize_cn_etf_pcf_delivery(
        frame,
        market_exchange=market_exchange,
        source_provider=source_provider,
        source_file=source.name,
    )
    result = audit_cn_etf_pcf_delivery(
        canonical,
        analysis_start=analysis_start,
        analysis_end=analysis_end,
    )
    result["canonical_columns"] = list(CANONICAL_COLUMNS)
    result["source"] = {
        "path": str(source),
        "sha256": sha256_file(source),
        "format": source.suffix.lower().lstrip("."),
        "provider": str(source_provider),
        "market_exchange": market_exchange.upper(),
        "rows": int(len(frame)),
        "normalized_rows": int(len(canonical)),
    }
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "cn_etf_pcf_delivery_validation.json"
    markdown_path = output / "cn_etf_pcf_delivery_validation.md"
    json_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render(result), encoding="utf-8")
    result["artifacts"] = {
        "json": str(json_path),
        "markdown": str(markdown_path),
    }
    return result


def _read_delivery(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"PCF delivery is missing: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, dtype_backend="numpy_nullable")
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError("PCF delivery must be CSV or Parquet")


def _render(result: dict[str, Any]) -> str:
    source = result["source"]
    decision = result["decision"]
    blockers = result.get("blockers", [])
    lines = [
        "# CN ETF PCF Delivery Validation",
        "",
        f"- Status: `{result['status']}`",
        f"- Provider: `{source['provider']}`",
        f"- Exchange: `{source['market_exchange']}`",
        f"- Source SHA-256: `{source['sha256']}`",
        f"- Rows: {result['rows']:,}",
        f"- Dates: {result['dates']:,}",
        f"- ETFs: {result['etfs']:,}",
        f"- Constituents: {result['constituents']:,}",
        f"- Structurally valid: {str(bool(decision['delivery_structurally_valid'])).lower()}",
        "- Source ready: false",
        "- Factor generation allowed: false",
        "",
        "A structurally valid delivery still requires full-history coverage, official "
        "calendar alignment, source fingerprinting, and point-in-time readiness review.",
        "",
    ]
    if blockers:
        lines.extend(["## Blockers", "", *[f"- `{value}`" for value in blockers], ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a local CN ETF PCF delivery without generating factors."
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--exchange", required=True, choices=("SSE", "SZSE"))
    parser.add_argument("--provider", required=True)
    parser.add_argument("--analysis-start", default="2020-01-02")
    parser.add_argument("--analysis-end", default="2024-06-28")
    parser.add_argument(
        "--output-dir",
        default="data/reports/cn_etf_pcf_delivery_validation",
    )
    args = parser.parse_args()
    result = validate_cn_etf_pcf_delivery(
        args.input,
        market_exchange=args.exchange,
        source_provider=args.provider,
        analysis_start=args.analysis_start,
        analysis_end=args.analysis_end,
        output_dir=args.output_dir,
    )
    print(
        json.dumps(
            {
                "stage": result["stage"],
                "status": result["status"],
                "source": result["source"],
                "blockers": result["blockers"],
                "decision": result["decision"],
                "artifacts": result["artifacts"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
