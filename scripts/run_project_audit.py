"""Run fast repository safety, boundary, and maintainability audit."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from quant_robot.audit.project_audit import collect_project_audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Quant Robot safety and maintainability audit.")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args(argv)

    audit = collect_project_audit(args.root)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0 if audit["summary"]["passes"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
