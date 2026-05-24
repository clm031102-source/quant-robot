from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.import_etf_csv import import_etf_csv


def batch_import_etf_csv(
    input_dir: str | Path,
    output_dir: str | Path,
    raw_dir: str | Path | None = None,
    move_raw: bool = False,
) -> dict[str, Any]:
    source_dir = Path(input_dir)
    output_root = Path(output_dir)
    raw_root = Path(raw_dir) if raw_dir is not None else None
    files = discover_etf_csv_files(source_dir)
    imports = []
    for csv_path in files:
        symbol = infer_symbol_from_filename(csv_path)
        import_path = _organize_raw_file(csv_path, symbol, raw_root, move_raw) if raw_root is not None else csv_path
        imports.append(import_etf_csv(import_path, output_root, symbol=symbol))

    result = {
        "files": len(files),
        "symbols": [item["symbol"] for item in imports],
        "total_rows": sum(int(item["rows"]) for item in imports),
        "raw_dir": str(raw_root) if raw_root is not None else None,
        "output_dir": str(output_root),
        "imports": imports,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "batch_import_manifest.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    return result


def discover_etf_csv_files(input_dir: str | Path) -> list[Path]:
    root = Path(input_dir)
    return sorted(path for path in root.glob("*.csv") if path.is_file())


def infer_symbol_from_filename(path: str | Path) -> str:
    file_path = Path(path)
    match = re.search(r"(?<!\d)(\d{6})(?!\d)", file_path.stem)
    if match is None:
        raise ValueError(f"Cannot infer ETF code from CSV filename: {file_path.name}")
    code = match.group(1)
    upper_name = file_path.stem.upper()
    if upper_name.startswith("SZSE"):
        return f"{code}.SZ"
    if upper_name.startswith("SSE"):
        return f"{code}.SH"
    if code.startswith(("15", "16")):
        return f"{code}.SZ"
    return f"{code}.SH"


def _organize_raw_file(csv_path: Path, symbol: str, raw_dir: Path | None, move_raw: bool) -> Path:
    if raw_dir is None:
        return csv_path
    raw_dir.mkdir(parents=True, exist_ok=True)
    target = raw_dir / _raw_filename(symbol)
    if csv_path.resolve() == target.resolve():
        return target
    if target.exists():
        target.unlink()
    if move_raw:
        csv_path.replace(target)
    else:
        target.write_bytes(csv_path.read_bytes())
    return target


def _raw_filename(symbol: str) -> str:
    code, suffix = symbol.split(".", 1)
    return f"{code}_{suffix}_1d.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch import TradingView A-share ETF CSV files into local processed bars.")
    parser.add_argument("--input-dir", default="data/raw/tradingview_etf_csv")
    parser.add_argument("--output-dir", default="data/processed/etf_csv")
    parser.add_argument("--raw-dir", default="data/raw/tradingview_etf_csv")
    parser.add_argument("--move-raw", action="store_true", help="Move files into --raw-dir using clean project filenames.")
    args = parser.parse_args()
    result = batch_import_etf_csv(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        raw_dir=Path(args.raw_dir) if args.raw_dir else None,
        move_raw=args.move_raw,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
