"""Export a read-only synthetic entitlement review; no broker or correction."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.execution.offline_corporate_review import build_corporate_action_review
from quant_robot.execution.offline_execution_evidence import load_execution_supplement
from quant_robot.execution.offline_runtime_health import ensure_distinct_paths, protected_paths
from quant_robot.storage.atomic import atomic_write


def _write_review_packet(path, packet, *, max_output_bytes=32_000_000):
    if type(max_output_bytes) is not int or not 0 < max_output_bytes <= 64_000_000:
        raise ValueError("invalid review output size limit")
    def writer(temporary):
        size = 0
        with temporary.open("wb") as target:
            for part in json.JSONEncoder(indent=2, sort_keys=True, allow_nan=False).iterencode(packet):
                encoded = part.encode("utf-8")
                size += len(encoded)
                if size > max_output_bytes:
                    raise ValueError("review exceeds output byte limit; previous report preserved")
                target.write(encoded)
    return atomic_write(path, writer)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execution-evidence", type=Path)
    parser.add_argument("--max-events", type=int, default=10_000)
    parser.add_argument("--max-payload-bytes", type=int, default=16_000_000)
    parser.add_argument("--max-output-bytes", type=int, default=32_000_000)
    args = parser.parse_args()
    try:
        ensure_distinct_paths({**protected_paths(args.journal, None), "review_output": args.output, "execution_evidence": args.execution_evidence})
        supplement = load_execution_supplement(args.execution_evidence) if args.execution_evidence is not None else None
        packet = build_corporate_action_review(args.journal, max_events=args.max_events, max_payload_bytes=args.max_payload_bytes,
            execution_supplement=supplement)
        _write_review_packet(args.output, packet, max_output_bytes=args.max_output_bytes)
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.error(str(exc))
    print(json.dumps({"status": packet["status"], "recorded_review_required": packet["recorded_corporate_review_required"],
        "actions": len(packet["actions"]), "journal_sequence": packet["journal"]["sequence"],
        "automatic_correction_allowed": False, "output": str(args.output.resolve())}))


if __name__ == "__main__":
    main()
