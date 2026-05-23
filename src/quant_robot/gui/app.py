from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from quant_robot.gui.research_service import (
    build_gui_snapshot,
    run_demo_paper_simulation,
    run_demo_research,
    run_demo_signal_snapshot,
)


def create_gui_handler(static_dir: Path | None = None) -> type[BaseHTTPRequestHandler]:
    root = static_dir or Path(__file__).with_name("static")

    class GuiRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/snapshot":
                self._send_json(build_gui_snapshot())
                return
            if parsed.path == "/api/research/demo":
                query = parse_qs(parsed.query)
                self._send_json(
                    run_demo_research(
                        market=_first(query, "market", "ALL"),
                        factor_name=_first(query, "factor", "momentum_2"),
                        top_n=int(_first(query, "top_n", "2")),
                        cost_bps=float(_first(query, "cost_bps", "5")),
                        start_date=_optional(query, "start_date"),
                        end_date=_optional(query, "end_date"),
                    )
                )
                return
            if parsed.path == "/api/signals/demo":
                query = parse_qs(parsed.query)
                self._send_json(
                    run_demo_signal_snapshot(
                        market=_first(query, "market", "ALL"),
                        factor_name=_first(query, "factor", "momentum_2"),
                        top_n=int(_first(query, "top_n", "2")),
                        as_of_date=_optional(query, "as_of_date"),
                        max_asset_weight=float(_first(query, "max_asset_weight", "1")),
                        max_market_weight=float(_first(query, "max_market_weight", "1")),
                        max_gross_exposure=float(_first(query, "max_gross_exposure", "1")),
                        min_cash_weight=float(_first(query, "min_cash_weight", "0")),
                        portfolio_value=float(_first(query, "portfolio_value", "100000")),
                    )
                )
                return
            if parsed.path == "/api/paper/demo":
                query = parse_qs(parsed.query)
                self._send_json(
                    run_demo_paper_simulation(
                        market=_first(query, "market", "ALL"),
                        factor_name=_first(query, "factor", "momentum_2"),
                        top_n=int(_first(query, "top_n", "2")),
                        start_date=_optional(query, "start_date"),
                        end_date=_optional(query, "end_date"),
                        initial_cash=float(_first(query, "initial_cash", "100000")),
                        commission_bps=float(_first(query, "commission_bps", "5")),
                        slippage_bps=float(_first(query, "slippage_bps", "5")),
                        max_asset_weight=float(_first(query, "max_asset_weight", "1")),
                        max_market_weight=float(_first(query, "max_market_weight", "1")),
                        max_gross_exposure=float(_first(query, "max_gross_exposure", "1")),
                        min_cash_weight=float(_first(query, "min_cash_weight", "0")),
                    )
                )
                return
            self._serve_static(parsed.path, root)

        def log_message(self, format: str, *args: object) -> None:
            return

        def _serve_static(self, path: str, static_root: Path) -> None:
            relative = "index.html" if path in {"", "/"} else path.lstrip("/")
            candidate = (static_root / relative).resolve()
            if not _is_within(candidate, static_root.resolve()) or not candidate.exists() or not candidate.is_file():
                self._send_text("Not found", status=404, content_type="text/plain; charset=utf-8")
                return
            content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(candidate.read_bytes())

        def _send_json(self, payload: object, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, body: str, status: int, content_type: str) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return GuiRequestHandler


def create_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), create_gui_handler())


def _first(query: dict[str, list[str]], key: str, default: str) -> str:
    values = query.get(key)
    return values[0] if values else default


def _optional(query: dict[str, list[str]], key: str) -> str | None:
    value = _first(query, key, "")
    return value or None


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
