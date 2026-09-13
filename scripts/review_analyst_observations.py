from __future__ import annotations

import argparse
import json

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.analyst_observation_bundle import materialize_observation_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description='Review supplied raw analyst observations offline; this does not admit a factor or certify historical availability.')
    parser.add_argument('--manifest', required=True, help='Explicit capture paths, SHA-256 fingerprints and aware observation times.')
    parser.add_argument('--as-of', required=True, help='Inclusive cutoff timestamp with timezone.')
    parser.add_argument('--output-dir', required=True, help='New output directory; existing directories are rejected.')
    args = parser.parse_args()
    try:
        result = materialize_observation_bundle(args.manifest, args.output_dir, as_of=args.as_of)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
