"""Zero-dependency local web server for Quant Robot v2 dashboard."""
from __future__ import annotations

import csv
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from quant_robot.audit.project_audit import collect_project_audit
from quant_robot.backtest.simulator import run_portfolio_backtest
from quant_robot.config.settings import (
    CostConfig,
    RiskConfig,
    StrategySpec,
    find_repo_root,
    load_backtest_presets,
    load_portfolios_config,
    resolve_data_root,
)
from quant_robot.data.readiness import check_parquet_readiness, check_tushare_readiness
from quant_robot.paper.runner import run_daily_paper_update
from quant_robot.reports.markdown import render_equity_svg
from quant_robot.storage.market_cache import MarketCache


def create_handler(
    *,
    repo_root: Path,
    data_root: Path,
    static_dir: Path | None = None,
) -> type[BaseHTTPRequestHandler]:
    assets_dir = static_dir or Path(__file__).with_name("static")
    paper_root = data_root / "paper"
    cache = MarketCache(data_root / "market_cache")

    class DashboardHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            try:
                if path == "/api/overview":
                    self._send_json(_load_overview(repo_root, data_root, cache))
                elif path.startswith("/api/portfolio/"):
                    pid = path.removeprefix("/api/portfolio/").strip("/")
                    detail = _load_portfolio_detail(paper_root, pid)
                    if detail is None:
                        self._send_json({"error": f"Portfolio not found: {pid}"}, HTTPStatus.NOT_FOUND)
                    else:
                        self._send_json(detail)
                elif path == "/api/presets":
                    presets_path = repo_root / "configs" / "backtest_presets.json"
                    presets = load_backtest_presets(presets_path).model_dump() if presets_path.is_file() else {"presets": []}
                    self._send_json(presets)
                elif path == "/api/system":
                    self._send_json(_system_status(repo_root, cache))
                else:
                    self._serve_static(path)
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            try:
                body = self._read_json_body()
                if path == "/api/paper/run":
                    skip_fetch = bool(body.get("skip_fetch", False))
                    cfg_path = repo_root / "configs" / "portfolios.json"
                    overview = run_daily_paper_update(
                        config_path=cfg_path,
                        data_root=data_root,
                        skip_fetch=skip_fetch,
                    )
                    self._send_json(overview)
                elif path == "/api/backtest/run":
                    result = _run_api_backtest(body, cache)
                    self._send_json(result)
                else:
                    self._send_json({"error": f"Unknown endpoint: {path}"}, HTTPStatus.NOT_FOUND)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def _read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError("JSON object body required")
            return parsed

        def _serve_static(self, url_path: str) -> None:
            rel = "index.html" if url_path in {"", "/"} else url_path.lstrip("/")
            candidate = (assets_dir / rel).resolve()
            if not candidate.is_relative_to(assets_dir.resolve()) or not candidate.is_file():
                self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
                return
            mime, _ = mimetypes.guess_type(str(candidate))
            payload = candidate.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{mime or 'application/octet-stream'}; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return DashboardHandler


def create_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    repo_root: str | Path | None = None,
    data_root: str | Path | None = None,
) -> ThreadingHTTPServer:
    root = find_repo_root(repo_root)
    droot = Path(data_root) if data_root is not None else resolve_data_root(root)
    handler = create_handler(repo_root=root, data_root=droot)
    return ThreadingHTTPServer((host, port), handler)


def run_dashboard(*, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = False) -> None:
    server = create_server(host=host, port=port)
    url = f"http://{host}:{port}"
    print(f"Quant Robot v2 Dashboard running at {url} (research-to-paper only; Ctrl+C to stop)")
    if open_browser:
        import webbrowser

        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _load_overview(repo_root: Path, data_root: Path, cache: MarketCache) -> dict[str, Any]:
    overview_file = data_root / "paper" / "overview.json"
    if overview_file.is_file():
        data = json.loads(overview_file.read_text(encoding="utf-8"))
        data["cache_symbols"] = len(cache.summary())
        return data
    cfg_path = repo_root / "configs" / "portfolios.json"
    cfg = load_portfolios_config(cfg_path) if cfg_path.is_file() else None
    portfolios = []
    if cfg:
        for p in cfg.portfolios:
            if not p.enabled:
                continue
            portfolios.append(
                {
                    "portfolio_id": p.portfolio_id,
                    "name": p.name,
                    "description": p.description,
                    "market": p.market,
                    "currency": p.currency,
                    "strategy_kind": p.strategy.kind,
                    "symbols": p.symbols,
                    "status": "not_initialized",
                    "days_recorded": 0,
                    "initial_cash": p.initial_cash,
                    "nav": p.initial_cash,
                    "cash": p.initial_cash,
                    "market_value": 0.0,
                    "net_pnl": 0.0,
                    "total_return": 0.0,
                    "max_drawdown": 0.0,
                    "trade_count": 0,
                    "total_fees": 0.0,
                    "positions_count": 0,
                }
            )
    return {
        "updated_at": None,
        "paper_only": True,
        "live_trading_allowed": False,
        "cache_symbols": len(cache.summary()),
        "portfolios": portfolios,
    }


def _load_portfolio_detail(paper_root: Path, portfolio_id: str) -> dict[str, Any] | None:
    pdir = (paper_root / portfolio_id).resolve()
    if not pdir.is_relative_to(paper_root.resolve()) or not (pdir / "state.json").is_file():
        return None
    state = json.loads((pdir / "state.json").read_text(encoding="utf-8"))
    signal = json.loads((pdir / "latest_signal.json").read_text(encoding="utf-8")) if (pdir / "latest_signal.json").is_file() else {}
    equity = _read_csv_rows(pdir / "equity.csv")
    trades = _read_csv_rows(pdir / "trades.csv")
    return {"state": state, "latest_signal": signal, "equity": equity, "trades": list(reversed(trades))[:100]}


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _system_status(repo_root: Path, cache: MarketCache) -> dict[str, Any]:
    audit = collect_project_audit(repo_root)
    return {
        "paper_only": True,
        "live_trading_allowed": False,
        "providers": {
            "tushare": check_tushare_readiness(),
            "parquet": check_parquet_readiness(),
        },
        "audit": audit["summary"],
        "cache": cache.summary(),
    }


def _run_api_backtest(body: dict[str, Any], cache: MarketCache) -> dict[str, Any]:
    market = str(body.get("market", "CN_ETF")).upper()
    raw_syms = body.get("symbols", [])
    if isinstance(raw_syms, str):
        symbols = [s.strip().upper() for s in raw_syms.split(",") if s.strip()]
    else:
        symbols = [str(s).strip().upper() for s in raw_syms if str(s).strip()]
    if not symbols:
        raise ValueError("At least one symbol is required")

    bars = cache.load_universe(market, symbols)
    if bars.empty:
        raise ValueError(f"No cached bars found for {market}: {symbols}. Click 'Update Data' first.")

    is_crypto = market == "CRYPTO"
    strategy = StrategySpec(
        kind=body.get("strategy_kind", "crypto_trend_vol" if is_crypto else "dual_momentum"),
        rebalance_frequency=body.get("rebalance_frequency", "weekly" if is_crypto else "monthly"),
        rebalance_band=float(body.get("rebalance_band") or (0.06 if is_crypto else 0.05)),
        lookback_days=int(body.get("lookback_days") or (40 if is_crypto else 60)),
        trend_ma_days=int(body.get("trend_ma_days") if body.get("trend_ma_days") not in (None, "") else (60 if is_crypto else 120)),
        vol_lookback_days=int(body.get("vol_lookback_days") or (30 if is_crypto else 60)),
        target_volatility=float(body.get("target_volatility") or 0.35),
        top_n=int(body.get("top_n") or 2),
        defensive_symbol=body.get("defensive_symbol") or None,
    )
    default_comm_bps = 10.0 if is_crypto else 1.0
    default_min_comm = 0.0 if is_crypto else (5.0 if market == "CN_ETF" else 1.0)
    default_slip_bps = 10.0 if is_crypto else 5.0
    cost = CostConfig(
        commission_bps=float(body["commission_bps"]) if body.get("commission_bps") not in (None, "") else default_comm_bps,
        minimum_commission=float(body["minimum_commission"]) if body.get("minimum_commission") not in (None, "") else default_min_comm,
        slippage_bps=float(body["slippage_bps"]) if body.get("slippage_bps") not in (None, "") else default_slip_bps,
    )
    risk = RiskConfig(
        max_drawdown_halt=float(body["max_drawdown_halt"]) if body.get("max_drawdown_halt") else None,
        cooldown_sessions=int(body.get("cooldown_sessions") or (7 if is_crypto else 5)),
        max_single_weight=1.0 if len(symbols) == 1 else float(body.get("max_single_weight") or 0.60),
    )
    default_lot = 0.0001 if is_crypto else (100.0 if market in {"CN_ETF", "CN"} else 1.0)
    lot_size = float(body["lot_size"]) if body.get("lot_size") not in (None, "") else default_lot
    min_trade_notional = float(body["min_trade_notional"]) if body.get("min_trade_notional") not in (None, "") else (10.0 if is_crypto else 0.0)
    report = run_portfolio_backtest(
        bars,
        name=str(body.get("name", f"{market} {strategy.kind}")),
        market=market,
        currency="CNY" if market in {"CN_ETF", "CN"} else "USD",
        symbols=symbols,
        strategy=strategy,
        cost=cost,
        risk=risk,
        initial_cash=float(body.get("initial_cash") or (10000.0 if market == "CN_ETF" else 1000.0)),
        lot_size=lot_size,
        min_trade_notional=min_trade_notional,
        start_date=body.get("start_date") or None,
        end_date=body.get("end_date") or None,
    )
    return {
        "summary": report.to_summary_dict(),
        "svg": render_equity_svg(report.equity_curve, f"{report.name} ({report.start_date} ~ {report.end_date})"),
        "trades": report.trades.tail(80).to_dict(orient="records") if not report.trades.empty else [],
    }
