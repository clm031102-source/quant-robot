"""Freeze source-only cadence inputs without computing real selection states."""
import argparse
import json
from pathlib import Path
import subprocess

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from quant_robot.research import geopolitical_cadence_study as study
from quant_robot.research.monthly_diagnostic_registration import (
    resolve_path, runtime_environment, sha256, write_exclusive_json,
)


def prepare(root, pilot_root):
    root, pilot_root = Path(root).resolve(), Path(pilot_root).resolve()
    study.require_unused(root)
    registration_path = resolve_path(root, study.REGISTRATION)
    if registration_path.exists():
        raise ValueError("Registration already frozen; preserve it before an explicit pre-execution revision")
    legacy = pilot_root/"data/reports/positive_ev_20260922"
    copies = {study.FROZEN[role]["path"]: legacy/path for role, (path, _) in study.PILOT_FILES.items()}
    for month in ("202203", "202512"):
        for part in study.PARTS:
            role = f"original_{month}_{part}"
            suffix = ".xls" if part == "vintage" else ".json"
            copies[study.AUTHORITY_PATHS[role]] = legacy/"geopolitical_source_pilot"/(month+"_"+part+suffix)
    for relative, original in copies.items():
        raw = original.read_bytes()
        target = resolve_path(root, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() != raw:
                raise ValueError("Retained pilot copy changed")
        else:
            with target.open("xb") as handle:
                handle.write(raw)
    inputs, snapshots = {}, {}
    paths = {**{role: item["path"] for role, item in study.FROZEN.items()}, **study.AUTHORITY_PATHS}
    for role, relative in paths.items():
        raw = resolve_path(root, relative).read_bytes()
        inputs[role] = dict(path=relative, sha256=sha256(raw))
        snapshots[role] = raw
    code = {path: dict(path=path, sha256=sha256(resolve_path(root, path).read_bytes()))
            for path in study.IMPLEMENTATION}
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip()
    packet = study.build_registration(inputs=inputs, code_files=code, branch=branch, environment=runtime_environment())
    study.source_chain(packet, snapshots)
    registration_path.parent.mkdir(parents=True, exist_ok=True)
    write_exclusive_json(registration_path, packet)
    raw = registration_path.read_bytes()
    scheduler_path = root/"configs/research_family_scheduler_cn_etf.json"
    scheduler = json.loads(scheduler_path.read_bytes())
    if study.DECISION in scheduler:
        raise ValueError("Existing geopolitical cadence decision must not be overwritten")
    scheduler[study.DECISION] = study.admission(packet, raw)
    scheduler_path.write_text(json.dumps(scheduler, ensure_ascii=False, indent=2)+"\n", encoding="utf-8", newline="\n")
    return dict(registration_id=packet["registration_id"], inputs=len(inputs), code_files=len(code),
                network_requests=0, states_generated=False, returns_computed=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--pilot-root", required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.root, args.pilot_root), indent=2))
