"""Fast, honest repository safety and maintainability audit.

Enforces three simple, high-signal engineering invariants:
1. Research-to-paper boundary: zero live broker/order placement calls in implementation code.
2. Secret & data hygiene: `.gitignore` blocks data/, .env, and credential files; no tokens in repo.
3. Maintainability: no bloated monster Python modules (>800 lines) in src/quant_robot/.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

FORBIDDEN_PATTERNS = (
    "place_order",
    "submit_order",
    "send_order",
    "cancel_order",
    "broker_adapter",
    "live_order",
    "account_login",
)
REQUIRED_GITIGNORE_RULES = ("data/", ".env", "*.parquet", "*.key", "*.pem", "*.sqlite")
SECRET_REGEX = re.compile(r"TUSHARE_TOKEN\s*=\s*['\"]?[A-Za-z0-9]{20,}", re.I)
MAX_MODULE_LINES = 800
SELF_FILE = "src/quant_robot/audit/project_audit.py"


def collect_project_audit(root: str | Path = ".") -> dict[str, Any]:
    root_path = Path(root).resolve()
    violations: list[dict[str, Any]] = []
    oversized: list[dict[str, Any]] = []
    scanned_files = 0
    src_modules = 0
    src_lines = 0

    for folder in ("src", "scripts", "quant_robot"):
        base = root_path / folder
        if not base.exists():
            continue
        for py in sorted(base.rglob("*.py")):
            if "__pycache__" in py.parts:
                continue
            rel = py.relative_to(root_path).as_posix()
            text = py.read_text(encoding="utf-8", errors="ignore")
            lines = text.splitlines()
            scanned_files += 1
            if rel.startswith("src/quant_robot/"):
                src_modules += 1
                src_lines += len(lines)
                if len(lines) > MAX_MODULE_LINES:
                    oversized.append({"path": rel, "lines": len(lines), "limit": MAX_MODULE_LINES})
            if rel == SELF_FILE:
                continue
            lower = text.lower()
            for pat in FORBIDDEN_PATTERNS:
                if pat in lower:
                    violations.append({"type": "forbidden_live_trading_pattern", "path": rel, "pattern": pat})
            if SECRET_REGEX.search(text):
                violations.append({"type": "hardcoded_secret", "path": rel})

    # Verify .gitignore covers data and secrets
    gitignore = root_path / ".gitignore"
    gi_lines = {l.strip() for l in gitignore.read_text(encoding="utf-8").splitlines()} if gitignore.is_file() else set()
    missing_gi = [rule for rule in REQUIRED_GITIGNORE_RULES if rule not in gi_lines]
    for rule in missing_gi:
        violations.append({"type": "missing_gitignore_rule", "rule": rule})

    passes = (len(violations) == 0) and (len(oversized) == 0)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "passes": passes,
            "scanned_files": scanned_files,
            "src_modules": src_modules,
            "src_lines": src_lines,
            "violation_count": len(violations),
            "oversized_count": len(oversized),
            "max_module_lines": MAX_MODULE_LINES,
            "live_trading_allowed": False,
        },
        "violations": violations,
        "oversized_modules": oversized,
    }
