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

from quant_robot.ops.factor_batch_readiness_gate import (  # noqa: E402
    build_factor_batch_readiness_gate,
    write_factor_batch_readiness_gate,
)
from scripts.run_cn_stock_local_source_queue_audit import run_cn_stock_local_source_queue_audit_cli  # noqa: E402
from scripts.run_factor_mining_candidate_plan_gate import run_factor_mining_candidate_plan_gate  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("data/reports/factor_batch_readiness_gate")


def run_factor_batch_readiness_gate(
    *,
    candidate_plan: str | Path,
    processed_root: str | Path = "data/processed",
    reports_root: str | Path = "data/reports",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    provider_request_allowed: bool = False,
    gate_stage: str = "discovery",
    allow_blocked: bool = False,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    source_queue_output = output_path / "source_queue"
    candidate_gate_output = output_path / "candidate_plan_gate"
    source_queue_packet = run_cn_stock_local_source_queue_audit_cli(
        processed_root=processed_root,
        reports_root=reports_root,
        output_dir=source_queue_output,
        provider_request_allowed=provider_request_allowed,
        fail_on_blocked=False,
    )
    candidate_gate_packet = run_factor_mining_candidate_plan_gate(
        candidate_plan=candidate_plan,
        local_source_queue_audit=source_queue_output / "cn_stock_local_source_queue_audit.json",
        gate_stage=gate_stage,
        output_dir=candidate_gate_output,
        allow_blocked=True,
    )
    packet = build_factor_batch_readiness_gate(
        source_queue_packet=source_queue_packet,
        candidate_plan_gate_packet=candidate_gate_packet,
        candidate_plan_path=candidate_plan,
        source_queue_output_dir=source_queue_output,
        candidate_plan_gate_output_dir=candidate_gate_output,
    )
    write_factor_batch_readiness_gate(output_path, packet)
    if not allow_blocked and not packet["decision"]["factor_batch_ready"]:
        blockers = ", ".join(packet["decision"].get("blockers", []) or [])
        raise RuntimeError(f"Factor batch readiness gate is blocked: {blockers}")
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the sequential CN stock factor-batch readiness gate.")
    parser.add_argument("--candidate-plan", required=True)
    parser.add_argument("--processed-root", default="data/processed")
    parser.add_argument("--reports-root", default="data/reports")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--provider-request-allowed", action="store_true")
    parser.add_argument("--gate-stage", choices=["discovery", "portfolio", "promotion"], default="discovery")
    parser.add_argument("--allow-blocked", action="store_true")
    args = parser.parse_args(argv)
    packet = run_factor_batch_readiness_gate(
        candidate_plan=args.candidate_plan,
        processed_root=args.processed_root,
        reports_root=args.reports_root,
        output_dir=args.output_dir,
        provider_request_allowed=args.provider_request_allowed,
        gate_stage=args.gate_stage,
        allow_blocked=args.allow_blocked,
    )
    print(
        json.dumps(
            {
                "status": packet["status"],
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
