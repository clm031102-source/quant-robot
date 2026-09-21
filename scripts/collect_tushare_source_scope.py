"""Collect one reviewed source scope; preview without network by default."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.config.secrets import require_env_secret  # noqa: E402
from quant_robot.data.sources.tushare_collection import collect_source  # noqa: E402
from quant_robot.storage.atomic import atomic_write_json  # noqa: E402
from scripts.run_quant_pm_startup_gate import run_quant_pm_startup_gate  # noqa: E402


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate scope JSON key")
        result[key] = value
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--machine", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--expected-scope-sha256")
    args = parser.parse_args(argv)
    try:
        scope_path = Path(args.scope).resolve()
        with scope_path.open("rb") as handle:
            raw_scope = handle.read(64_001)
        if len(raw_scope) > 64_000:
            raise ValueError("scope exceeds 64000 bytes")
        scope = json.loads(raw_scope.decode("utf-8-sig"), object_pairs_hook=_unique_keys)

        def fresh_gate(output: Path) -> dict:
            invocation = {"entrypoint_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "scope_file_sha256": hashlib.sha256(raw_scope).hexdigest(),
                "machine": args.machine, "task": "factor_review", "branch": args.branch}
            atomic_write_json(output.parent / "invocation.json", invocation)
            return run_quant_pm_startup_gate(output_dir=output, machine=args.machine,
                task="factor_review", branch=args.branch)

        result = collect_source(scope, repo_root=Path.cwd(), run_gate=fresh_gate,
            get_token=lambda: require_env_secret("TUSHARE_TOKEN"), execute=args.execute,
            expected_scope_sha256=args.expected_scope_sha256)
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "rejected", "failure_kind": type(exc).__name__}))
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["status"] in {"preview", "collected_unqualified"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
