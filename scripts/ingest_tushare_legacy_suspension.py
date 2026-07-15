from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.adapters.tushare_adapter import TushareAdapter
from quant_robot.data.ingest.tushare_legacy_suspension import (
    TushareLegacySuspensionAdapter,
    run_tushare_legacy_suspension_ingest,
)


DEFAULT_OUTPUT_DIR = Path("data/processed/cn_stock_legacy_suspension_20260716")


def run_legacy_suspension_ingest(
    *,
    unresolved_assets_path: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    start_date: str = "2015-01-01",
    end_date: str = "2025-12-31",
    adapter: TushareLegacySuspensionAdapter | None = None,
    bse_code_mapping_path: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(unresolved_assets_path)
    if not path.is_file():
        raise FileNotFoundError(f"unresolved asset list does not exist: {path}")
    unresolved = pd.read_csv(path)
    mapping_source = None
    if bse_code_mapping_path is not None:
        mapping_path = Path(bse_code_mapping_path)
        unresolved = _apply_bse_code_mapping(unresolved, mapping_path)
        mapping_source = f"{mapping_path}#sha256={hashlib.sha256(mapping_path.read_bytes()).hexdigest()}"
    return run_tushare_legacy_suspension_ingest(
        adapter or TushareAdapter(),
        unresolved,
        start_date,
        end_date,
        output_dir,
        provider_mapping_source=mapping_source,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch legacy Tushare suspension intervals only for unresolved CN stock assets."
    )
    parser.add_argument("--unresolved-assets", required=True)
    parser.add_argument("--start-date", default="2015-01-01")
    parser.add_argument("--end-date", default="2025-12-31")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--bse-code-mapping-html")
    args = parser.parse_args()
    report = run_legacy_suspension_ingest(
        unresolved_assets_path=args.unresolved_assets,
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir,
        bse_code_mapping_path=args.bse_code_mapping_html,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


def _apply_bse_code_mapping(unresolved: pd.DataFrame, path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"BSE code mapping HTML does not exist: {path}")
    tables = pd.read_html(path, header=0)
    table = next((value for value in tables if value.shape[1] >= 5), None)
    if table is None:
        raise ValueError(f"BSE code mapping HTML has no five-column mapping table: {path}")
    old_codes = _code_series(table.iloc[:, 3])
    new_codes = _code_series(table.iloc[:, 4])
    mapping_frame = pd.DataFrame({"old_code": old_codes, "new_code": new_codes}).dropna()
    if mapping_frame["new_code"].duplicated().any():
        raise ValueError("BSE code mapping contains duplicate new codes")
    mapping = dict(zip(mapping_frame["new_code"], mapping_frame["old_code"]))
    output = unresolved.copy()
    if "symbol" not in output:
        raise ValueError("unresolved asset list missing symbol column")
    output["symbol"] = output["symbol"].astype(str).str.strip().str.upper()
    output["provider_symbol"] = output["symbol"]
    bse_mask = output["symbol"].str.endswith(".BJ")
    current_codes = output.loc[bse_mask, "symbol"].str.split(".", regex=False).str[0]
    historical_codes = current_codes.map(mapping)
    mapped_mask = historical_codes.notna()
    output.loc[historical_codes.index[mapped_mask], "provider_symbol"] = (
        historical_codes.loc[mapped_mask] + ".BJ"
    )
    return output


def _code_series(values: pd.Series) -> pd.Series:
    text = values.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    valid = text.str.fullmatch(r"\d{1,6}", na=False)
    return text.where(valid).str.zfill(6)


if __name__ == "__main__":
    main()
