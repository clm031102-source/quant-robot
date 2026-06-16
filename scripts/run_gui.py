from __future__ import annotations

import argparse

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.gui.app import create_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Quant Robot research GUI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()

    server = create_server(args.host, args.port)
    print(f"Quant Robot GUI running at http://{args.host}:{args.port}")
    print("Research-only mode: no broker connection, no order placement, no live trading.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Quant Robot GUI.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
