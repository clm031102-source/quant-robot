from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from quant_robot.gui.control_center import build_control_center_snapshot, run_verification_gate
from quant_robot.gui.operation_ledger import append_operation_ledger_entry, build_operation_ledger_snapshot
from quant_robot.gui.research_service import (
    build_constrained_search_snapshot,
    build_daily_ops_snapshot,
    build_evidence_refresh_snapshot,
    build_expanded_observation_replay_snapshot,
    build_promotion_ops_snapshot,
    build_promotion_review_snapshot,
    build_gui_snapshot,
    build_iterative_observation_expansion_snapshot,
    build_observation_sufficiency_snapshot,
    build_paper_profile_snapshot,
    build_post_refresh_replay_snapshot,
    build_profile_observation_snapshot,
    build_project_status_snapshot,
    build_recent_data_refresh_snapshot,
    build_risk_candidate_snapshot,
    build_tushare_activation_gate_snapshot,
    run_demo_paper_simulation,
    run_demo_research,
    run_demo_signal_snapshot,
    run_gui_paper_simulation,
    run_gui_research,
    run_gui_signal_snapshot,
)


def create_gui_handler(static_dir: Path | None = None) -> type[BaseHTTPRequestHandler]:
    root = static_dir or Path(__file__).with_name("static")

    class GuiRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/control/status":
                self._send_json(build_control_center_snapshot())
                return
            if parsed.path == "/api/control/operation-ledger":
                self._send_json(build_operation_ledger_snapshot(Path.cwd()))
                return
            if parsed.path == "/api/control/verification":
                query = parse_qs(parsed.query)
                gate_id = _first(query, "gate_id", "")
                result = run_verification_gate(gate_id=gate_id)
                _record_operation(
                    workflow_id="verification_runner",
                    label=f"Run verification gate {gate_id}",
                    status=result.get("status", "unknown"),
                    command=f"GET {parsed.path}?{parsed.query}",
                    request={"gate_id": gate_id},
                    result=result,
                )
                self._send_json(result)
                return
            if parsed.path == "/api/snapshot":
                self._send_json(build_gui_snapshot())
                return
            if parsed.path == "/api/project/status":
                query = parse_qs(parsed.query)
                self._send_json(
                    build_project_status_snapshot(
                        readiness_board=_optional(query, "readiness_board"),
                        data_gap_evidence=_optional(query, "data_gap_evidence"),
                        provider_remediation=_optional(query, "provider_remediation"),
                        residual_focus=_optional(query, "residual_focus"),
                    )
                )
                return
            if parsed.path == "/api/daily/ops":
                query = parse_qs(parsed.query)
                self._send_json(build_daily_ops_snapshot(daily_ops_pack=_optional(query, "daily_ops_pack")))
                return
            if parsed.path == "/api/risk/candidates":
                query = parse_qs(parsed.query)
                self._send_json(build_risk_candidate_snapshot(risk_candidate_pack=_optional(query, "risk_candidate_pack")))
                return
            if parsed.path == "/api/risk/constrained-search":
                query = parse_qs(parsed.query)
                self._send_json(build_constrained_search_snapshot(constrained_search_pack=_optional(query, "constrained_search_pack")))
                return
            if parsed.path == "/api/risk/paper-profiles":
                query = parse_qs(parsed.query)
                self._send_json(build_paper_profile_snapshot(paper_profile_pack=_optional(query, "paper_profile_pack")))
                return
            if parsed.path == "/api/risk/profile-observation":
                query = parse_qs(parsed.query)
                self._send_json(
                    build_profile_observation_snapshot(
                        profile_observation_pack=_optional(query, "profile_observation_pack")
                    )
                )
                return
            if parsed.path == "/api/data/recent-refresh":
                query = parse_qs(parsed.query)
                self._send_json(
                    build_recent_data_refresh_snapshot(
                        recent_data_refresh_pack=_optional(query, "recent_data_refresh_pack")
                    )
                )
                return
            if parsed.path == "/api/data/post-refresh-replay":
                query = parse_qs(parsed.query)
                self._send_json(
                    build_post_refresh_replay_snapshot(
                        post_refresh_replay_pack=_optional(query, "post_refresh_replay_pack")
                    )
                )
                return
            if parsed.path == "/api/risk/observation-sufficiency":
                query = parse_qs(parsed.query)
                self._send_json(
                    build_observation_sufficiency_snapshot(
                        observation_sufficiency_pack=_optional(query, "observation_sufficiency_pack")
                    )
                )
                return
            if parsed.path == "/api/risk/expanded-observation-replay":
                query = parse_qs(parsed.query)
                self._send_json(
                    build_expanded_observation_replay_snapshot(
                        expanded_observation_replay_pack=_optional(query, "expanded_observation_replay_pack")
                    )
                )
                return
            if parsed.path == "/api/risk/iterative-observation-expansion":
                query = parse_qs(parsed.query)
                self._send_json(
                    build_iterative_observation_expansion_snapshot(
                        iterative_observation_expansion_pack=_optional(query, "iterative_observation_expansion_pack")
                    )
                )
                return
            if parsed.path == "/api/risk/tushare-activation-gate":
                query = parse_qs(parsed.query)
                self._send_json(
                    build_tushare_activation_gate_snapshot(
                        tushare_activation_gate_pack=_optional(query, "tushare_activation_gate_pack")
                    )
                )
                return
            if parsed.path == "/api/research":
                query = parse_qs(parsed.query)
                result = run_gui_research(
                    source=_first(query, "source", "demo_fixture"),
                    data_root=_optional(query, "data_root"),
                    market=_first(query, "market", "ALL"),
                    factor_name=_first(query, "factor", "momentum_2"),
                    factor_windows=_optional_windows(query, "factor_windows"),
                    top_n=int(_first(query, "top_n", "2")),
                    cost_bps=float(_first(query, "cost_bps", "5")),
                    start_date=_optional(query, "start_date"),
                    end_date=_optional(query, "end_date"),
                    forward_horizon=int(_first(query, "forward_horizon", "1")),
                    execution_lag=int(_first(query, "execution_lag", "1")),
                    rebalance_interval=int(_first(query, "rebalance_interval", "1")),
                    portfolio_scope=_optional(query, "portfolio_scope"),
                    periods_per_year=_optional_float(query, "periods_per_year"),
                    benchmark_asset_id=_optional(query, "benchmark_asset_id"),
                    cash_annual_return=float(_first(query, "cash_annual_return", "0")),
                    regime_filter=_bool(_first(query, "regime_filter", "false")),
                    regime_lookback=int(_first(query, "regime_lookback", "20")),
                    min_relative_return=_optional_float(query, "min_relative_return"),
                    max_drawdown_limit=_optional_float(query, "max_drawdown_limit"),
                )
                _record_operation(
                    workflow_id="research_backtest",
                    label="Run research backtest",
                    status="completed",
                    command=f"GET {parsed.path}?{parsed.query}",
                    request=result.get("request", {}),
                    result=result,
                )
                self._send_json(result)
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
                        benchmark_asset_id=_optional(query, "benchmark_asset_id"),
                        cash_annual_return=float(_first(query, "cash_annual_return", "0")),
                        regime_filter=_bool(_first(query, "regime_filter", "false")),
                        regime_lookback=int(_first(query, "regime_lookback", "20")),
                        min_relative_return=_optional_float(query, "min_relative_return"),
                        max_drawdown_limit=_optional_float(query, "max_drawdown_limit"),
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
            if parsed.path == "/api/signals":
                query = parse_qs(parsed.query)
                result = run_gui_signal_snapshot(
                    source=_first(query, "source", "demo_fixture"),
                    data_root=_optional(query, "data_root"),
                    market=_first(query, "market", "ALL"),
                    factor_name=_first(query, "factor", "momentum_2"),
                    factor_windows=_optional_windows(query, "factor_windows"),
                    top_n=int(_first(query, "top_n", "2")),
                    as_of_date=_optional(query, "as_of_date"),
                    max_asset_weight=float(_first(query, "max_asset_weight", "1")),
                    max_market_weight=float(_first(query, "max_market_weight", "1")),
                    max_gross_exposure=float(_first(query, "max_gross_exposure", "1")),
                    min_cash_weight=float(_first(query, "min_cash_weight", "0")),
                    portfolio_value=float(_first(query, "portfolio_value", "100000")),
                )
                _record_operation(
                    workflow_id="signal_snapshot",
                    label="Generate advisory signal snapshot",
                    status="completed",
                    command=f"GET {parsed.path}?{parsed.query}",
                    request=result.get("request", {}),
                    result=result,
                )
                self._send_json(result)
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
                        max_drawdown_guard=_optional_float(query, "max_drawdown_guard"),
                        guard_cooldown_periods=int(_first(query, "guard_cooldown_periods", "0")),
                    )
                )
                return
            if parsed.path == "/api/paper":
                query = parse_qs(parsed.query)
                result = run_gui_paper_simulation(
                    source=_first(query, "source", "demo_fixture"),
                    data_root=_optional(query, "data_root"),
                    market=_first(query, "market", "ALL"),
                    factor_name=_first(query, "factor", "momentum_2"),
                    factor_windows=_optional_windows(query, "factor_windows"),
                    top_n=int(_first(query, "top_n", "2")),
                    rebalance_interval=int(_first(query, "rebalance_interval", "1")),
                    start_date=_optional(query, "start_date"),
                    end_date=_optional(query, "end_date"),
                    initial_cash=float(_first(query, "initial_cash", "100000")),
                    commission_bps=float(_first(query, "commission_bps", "5")),
                    slippage_bps=float(_first(query, "slippage_bps", "5")),
                    max_asset_weight=float(_first(query, "max_asset_weight", "1")),
                    max_market_weight=float(_first(query, "max_market_weight", "1")),
                    max_gross_exposure=float(_first(query, "max_gross_exposure", "1")),
                    min_cash_weight=float(_first(query, "min_cash_weight", "0")),
                    periods_per_year=_optional_float(query, "periods_per_year"),
                    max_drawdown_guard=_optional_float(query, "max_drawdown_guard"),
                    guard_cooldown_periods=int(_first(query, "guard_cooldown_periods", "0")),
                )
                _record_operation(
                    workflow_id="paper_simulation",
                    label="Run local paper simulation",
                    status="completed",
                    command=f"GET {parsed.path}?{parsed.query}",
                    request=result.get("request", {}),
                    result=result,
                )
                self._send_json(result)
                return
            if parsed.path == "/api/promotion/ops":
                query = parse_qs(parsed.query)
                self._send_json(
                    build_promotion_ops_snapshot(
                        promotion_report=_optional(query, "promotion_report"),
                        provider_status=_optional(query, "provider_status"),
                        quality_report=_optional(query, "quality_report"),
                    )
                )
                return
            if parsed.path == "/api/promotion/review":
                query = parse_qs(parsed.query)
                self._send_json(
                    build_promotion_review_snapshot(
                        promotion_report=_optional(query, "promotion_report"),
                        provider_status=_optional(query, "provider_status"),
                        quality_report=_optional(query, "quality_report"),
                        candidate_id=_optional(query, "candidate_id"),
                    )
                )
                return
            if parsed.path == "/api/promotion/evidence-refresh":
                query = parse_qs(parsed.query)
                self._send_json(
                    build_evidence_refresh_snapshot(
                        promotion_report=_optional(query, "promotion_report"),
                        provider_status=_optional(query, "provider_status"),
                        quality_report=_optional(query, "quality_report"),
                        candidate_id=_optional(query, "candidate_id"),
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


def _record_operation(
    *,
    workflow_id: str,
    label: str,
    status: str,
    command: str,
    request: dict[str, object] | None,
    result: dict[str, object],
) -> None:
    try:
        append_operation_ledger_entry(
            repo_root=Path.cwd(),
            workflow_id=workflow_id,
            label=label,
            status=status,
            command=command,
            request=request if isinstance(request, dict) else {},
            result=result,
        )
    except OSError:
        return


def _first(query: dict[str, list[str]], key: str, default: str) -> str:
    values = query.get(key)
    return values[0] if values else default


def _optional(query: dict[str, list[str]], key: str) -> str | None:
    value = _first(query, key, "")
    return value or None


def _optional_float(query: dict[str, list[str]], key: str) -> float | None:
    value = _optional(query, key)
    return float(value) if value is not None else None


def _optional_windows(query: dict[str, list[str]], key: str) -> tuple[int, ...] | None:
    value = _optional(query, key)
    if value is None:
        return None
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def _bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
