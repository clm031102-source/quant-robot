from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.cn_stock_local_source_queue_audit import (  # noqa: E402
    build_cn_stock_local_source_queue_audit,
    write_cn_stock_local_source_queue_audit,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/cn_stock_local_source_queue_audit")


def run_cn_stock_local_source_queue_audit_cli(
    *,
    processed_root: str | Path = "data/processed",
    reports_root: str | Path = "data/reports",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    provider_request_allowed: bool = False,
    fail_on_blocked: bool = False,
) -> dict[str, Any]:
    packet = build_cn_stock_local_source_queue_audit(
        processed_root=processed_root,
        reports_root=reports_root,
        provider_request_allowed=provider_request_allowed,
    )
    write_cn_stock_local_source_queue_audit(output_dir, packet)
    if fail_on_blocked and packet["decision"]["status"] != "cleared":
        blockers = ", ".join(packet["decision"].get("blockers", []) or [])
        raise RuntimeError(f"CN stock local source queue audit is blocked: {blockers}")
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit CN stock local source queue readiness.")
    parser.add_argument("--processed-root", default="data/processed")
    parser.add_argument("--reports-root", default="data/reports")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--provider-request-allowed", action="store_true")
    parser.add_argument("--fail-on-blocked", action="store_true")
    args = parser.parse_args(argv)
    packet = run_cn_stock_local_source_queue_audit_cli(
        processed_root=args.processed_root,
        reports_root=args.reports_root,
        output_dir=args.output_dir,
        provider_request_allowed=args.provider_request_allowed,
        fail_on_blocked=args.fail_on_blocked,
    )
    print(
        json.dumps(
            {
                "status": packet["decision"]["status"],
                "summary": packet["summary"],
                "decision": packet["decision"],
                "output_dir": str(Path(args.output_dir)),
                "safety": packet.get("safety", ""),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
