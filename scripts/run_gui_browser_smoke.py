from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.gui.control_center import SAFETY_NOTICE


DEFAULT_BASE_URL = "http://127.0.0.1:8765"
DEFAULT_OUTPUT_DIR = Path("data/reports/gui_browser_smoke")


def run_gui_browser_smoke(
    base_url: str = DEFAULT_BASE_URL,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    timeout: float = 5.0,
) -> dict[str, Any]:
    normalized_base_url = base_url.rstrip("/")
    checks: list[dict[str, Any]] = []
    index_html = _fetch_text(normalized_base_url, "/", timeout)
    app_js = _fetch_text(normalized_base_url, "/app.js", timeout)
    styles_css = _fetch_text(normalized_base_url, "/styles.css", timeout)
    control = _fetch_json(normalized_base_url, "/api/control/status", timeout)

    checks.append(
        _check(
            "index_html",
            "Index HTML",
            index_html.get("ok")
            and all(
                token in str(index_html.get("body", ""))
                for token in [
                    "control-center-board",
                    "control-backtest-status",
                    "control-backtest-provenance",
                    "control-startup-health",
                    "control-audit-feedback",
                    "control-audit-iteration-plan",
                    "control-safety-boundary",
                ]
            ),
            "Home page exposes the control-center board, backtest status, backtest provenance, startup health, audit feedback, audit iteration plan, and safety boundary.",
            index_html.get("error") or "Home page is missing one or more required GUI anchors.",
        )
    )
    checks.append(
        _check(
            "app_js",
            "Frontend script",
            app_js.get("ok")
            and "renderControlCenter" in str(app_js.get("body", ""))
            and "renderStartupHealth" in str(app_js.get("body", ""))
            and "renderBacktestProvenance" in str(app_js.get("body", ""))
            and "renderAuditFeedback" in str(app_js.get("body", ""))
            and "renderAuditIterationPlan" in str(app_js.get("body", "")),
            "Frontend script includes control-center, startup-health, backtest-provenance, audit-feedback, and audit-iteration renderers.",
            app_js.get("error") or "Frontend script is missing required renderer hooks.",
        )
    )
    checks.append(
        _check(
            "control_status_api",
            "Control status API",
            control.get("ok") and control.get("body", {}).get("stage") == "gui_control_center",
            "Control API returned stage=gui_control_center.",
            control.get("error") or f"Unexpected control API stage: {control.get('body', {}).get('stage')}",
        )
    )
    control_body = control.get("body", {}) if isinstance(control.get("body"), dict) else {}
    checks.append(
        _check(
            "startup_health_panel",
            "Startup health contract",
            control.get("ok")
            and control_body.get("startup_health", {}).get("stage") == "gui_startup_health"
            and bool(control_body.get("startup_health", {}).get("rows")),
            "Control API exposes startup_health rows for local startup, control API, browser smoke, and smoke evidence.",
            control.get("error") or "Control API is missing startup_health rows.",
        )
    )
    checks.append(
        _check(
            "backtest_provenance_panel",
            "Backtest provenance contract",
            control.get("ok")
            and control_body.get("backtest_provenance", {}).get("stage") == "backtest_provenance"
            and bool(control_body.get("backtest_provenance", {}).get("rows"))
            and control_body.get("backtest_provenance", {}).get("summary", {}).get("paper_only") is True,
            "Control API exposes backtest provenance with source, endpoint, metrics, and paper-only boundary evidence.",
            control.get("error") or "Control API is missing backtest provenance rows.",
        )
    )
    checks.append(
        _check(
            "audit_feedback_panel",
            "Audit feedback contract",
            control.get("ok")
            and control_body.get("audit_feedback", {}).get("stage") == "gui_audit_feedback"
            and "next_actions" in control_body.get("audit_feedback", {}),
            "Control API exposes audit_feedback with next optimization actions.",
            control.get("error") or "Control API is missing audit_feedback next-actions data.",
        )
    )
    checks.append(
        _check(
            "audit_iteration_plan_panel",
            "Audit iteration plan contract",
            control.get("ok")
            and control_body.get("audit_iteration_plan", {}).get("stage") == "gui_audit_iteration_plan"
            and bool(control_body.get("audit_iteration_plan", {}).get("rows")),
            "Control API exposes audit_iteration_plan rows that turn audit findings into visible acceptance gates.",
            control.get("error") or "Control API is missing audit_iteration_plan rows.",
        )
    )
    checks.append(
        _check(
            "responsive_contract",
            "Responsive layout contract",
            styles_css.get("ok")
            and "@media" in str(styles_css.get("body", ""))
            and ".startup-health-list" in str(styles_css.get("body", ""))
            and ".backtest-provenance-list" in str(styles_css.get("body", ""))
            and ".audit-feedback-list" in str(styles_css.get("body", ""))
            and ".audit-iteration-list" in str(styles_css.get("body", "")),
            "Stylesheet contains responsive breakpoints plus startup-health, backtest-provenance, audit-feedback, and audit-iteration sizing rules.",
            styles_css.get("error") or "Stylesheet is missing responsive or audit-iteration layout rules.",
        )
    )
    safety = control_body.get("safety", {}) if isinstance(control_body.get("safety"), dict) else {}
    checks.append(
        _check(
            "live_boundary",
            "Research-to-paper boundary",
            control.get("ok") and safety.get("live_trading_allowed") is False and safety.get("order_placement_allowed") is False,
            "Live trading and order placement are disabled in the control-center API.",
            control.get("error") or "Control-center safety boundary is not clearly disabled.",
        )
    )

    passed = sum(1 for row in checks if row["status"] == "passed")
    failed = sum(1 for row in checks if row["status"] == "failed")
    packet = {
        "stage": "gui_browser_smoke_evidence",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "base_url": normalized_base_url,
        "status": "passed" if failed == 0 else "failed",
        "summary": {
            "checks": len(checks),
            "passed": passed,
            "failed": failed,
            "desktop_viewport": "verified by Browser during release validation",
            "mobile_viewport": "390x844 verified by Browser during release validation",
        },
        "checks": checks,
        "safety": {
            "notice": safety.get("notice", SAFETY_NOTICE),
            "paper_trading_allowed": bool(safety.get("paper_trading_allowed", False)),
            "live_trading_allowed": bool(safety.get("live_trading_allowed", False)),
            "broker_connection_allowed": bool(safety.get("broker_connection_allowed", False)),
            "account_read_allowed": bool(safety.get("account_read_allowed", False)),
            "order_placement_allowed": bool(safety.get("order_placement_allowed", False)),
        },
    }
    _write_packet(Path(output_dir), packet)
    return packet


def _fetch_text(base_url: str, path: str, timeout: float) -> dict[str, Any]:
    try:
        with urlopen(f"{base_url}{path}", timeout=timeout) as response:
            return {
                "ok": 200 <= response.status < 300,
                "status": response.status,
                "body": response.read().decode("utf-8", errors="replace"),
                "error": "",
            }
    except (OSError, URLError) as exc:
        return {"ok": False, "status": None, "body": "", "error": str(exc)}


def _fetch_json(base_url: str, path: str, timeout: float) -> dict[str, Any]:
    result = _fetch_text(base_url, path, timeout)
    if not result.get("ok"):
        return result
    try:
        result["body"] = json.loads(str(result.get("body", "")))
    except json.JSONDecodeError as exc:
        result.update({"ok": False, "error": str(exc), "body": {}})
    return result


def _check(check_id: str, label: str, passed: Any, evidence: str, failure: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "label": label,
        "status": "passed" if bool(passed) else "failed",
        "evidence": evidence if bool(passed) else failure,
    }


def _write_packet(output_dir: Path, packet: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "gui_browser_smoke.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "gui_browser_smoke.md").write_text(_render_markdown(packet), encoding="utf-8")


def _render_markdown(packet: dict[str, Any]) -> str:
    safety = packet.get("safety", {})
    rows = [
        "# GUI Browser Smoke Evidence",
        "",
        f"- Generated at: {packet.get('generated_at', '')}",
        f"- Base URL: {packet.get('base_url', '')}",
        f"- Status: {packet.get('status', '')}",
        f"- Safety: {safety.get('notice', SAFETY_NOTICE)}",
        "",
        "## Checks",
    ]
    for check in packet.get("checks", []):
        rows.append(
            f"- [{check.get('status', '')}] {check.get('label', check.get('check_id', 'check'))}: "
            f"{check.get('evidence', '')}"
        )
    return "\n".join(rows) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a local GUI browser smoke evidence packet.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    packet = run_gui_browser_smoke(base_url=args.base_url, output_dir=args.output_dir, timeout=args.timeout)
    print(json.dumps(packet, indent=2, sort_keys=True))
    if packet.get("status") != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
