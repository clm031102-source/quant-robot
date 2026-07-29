from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.cn_etf_broker_adapter_contract import (  # noqa: E402
    build_cn_etf_broker_adapter_contract_readiness,
)
from quant_robot.storage.atomic import atomic_write_json, atomic_write_text  # noqa: E402


DEFAULT_CONFIG = Path("configs/cn_etf_broker_adapter_contract_20260729.json")
DEFAULT_OUTPUT_DIR = Path(
    "data/reports/cn_etf_broker_adapter_contract_readiness_20260729"
)


def run_cn_etf_broker_adapter_contract_readiness_cli(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    config = _load_json(Path(config_path))
    result = build_cn_etf_broker_adapter_contract_readiness(config)
    destination = Path(output_dir)
    json_path = atomic_write_json(
        destination / "cn_etf_broker_adapter_contract_readiness.json",
        result,
    )
    markdown_path = atomic_write_text(
        destination / "cn_etf_broker_adapter_contract_readiness.md",
        _render(result),
    )
    result["artifacts"] = {
        "json": str(json_path),
        "markdown": str(markdown_path),
    }
    return result


def _render(result: dict[str, Any]) -> str:
    paper = result["paper_gates"]
    risk = result["risk_contract"]
    lines = [
        "# CN ETF Broker Adapter Contract Readiness",
        "",
        f"- Status: `{result['status']}`",
        f"- Broker selected: `{result['broker'].get('provider', 'unselected')}`",
        f"- Schema validation allowed: {str(result['schema_validation_allowed']).lower()}",
        f"- Broker connection allowed: {str(result['broker_connection_allowed']).lower()}",
        f"- Account read allowed: {str(result['account_read_allowed']).lower()}",
        f"- Order placement allowed: {str(result['order_placement_allowed']).lower()}",
        f"- Live boundary allowed: {str(result['live_boundary_allowed']).lower()}",
        "",
        "## Frozen Risk Contract",
        "",
        f"- Capital: CNY {risk['capital_cny']['minimum']}-{risk['capital_cny']['maximum']}",
        f"- Max single position: CNY {risk['max_single_position_cny']}",
        f"- Max daily loss: CNY {risk['max_daily_loss_cny']}",
        f"- Absolute maximum drawdown: {risk['absolute_max_drawdown']:.0%}",
        f"- Paper drawdown gate: {risk['paper_promotion_max_drawdown']:.0%}",
        "",
        "## Physical Paper Gates",
        "",
        f"- Minimum observation days: {paper['minimum_days']}",
        f"- Minimum simulated fills: {paper['minimum_fills']}",
        f"- Minimum market regimes: {paper['minimum_market_regimes']}",
        "",
        "## Missing Broker Inputs",
        "",
    ]
    lines.extend(
        f"- {value}" for value in result["required_broker_onboarding_inputs"]
    )
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- `{value}`" for value in result["blockers"]) if result[
        "blockers"
    ] else lines.append("- None")
    lines.extend(
        [
            "",
            "This packet validates an offline interface contract only. It does not "
            "connect to a broker, read an account, place an order, or authorize live trading.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"broker adapter contract does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid broker adapter contract: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("broker adapter contract must be a JSON object")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate the disabled CN ETF broker adapter contract."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    result = run_cn_etf_broker_adapter_contract_readiness_cli(
        config_path=args.config,
        output_dir=args.output_dir,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "blockers": result["blockers"],
                "broker_connection_allowed": result[
                    "broker_connection_allowed"
                ],
                "account_read_allowed": result["account_read_allowed"],
                "order_placement_allowed": result["order_placement_allowed"],
                "live_boundary_allowed": result["live_boundary_allowed"],
                "artifacts": result["artifacts"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
