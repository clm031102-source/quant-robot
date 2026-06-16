"""Compatibility shim for running this src-layout checkout without install."""

from __future__ import annotations

from pathlib import Path


_SRC_PACKAGE = Path(__file__).resolve().parents[1] / "src" / "quant_robot"

if not _SRC_PACKAGE.is_dir():  # pragma: no cover - defensive guard for broken checkouts
    raise ImportError(f"Workspace source package not found: {_SRC_PACKAGE}")

__path__ = [str(_SRC_PACKAGE)]
__all__ = ["__version__"]
__version__ = "0.1.0"
