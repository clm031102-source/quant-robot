"""Unified, atomic, idempotent, auto-backfilling paper-trading portfolio ledger.

Research-to-paper ONLY: never connects to a broker, never reads real accounts, never places live orders.
If one or more sessions were missed (PC off, network blip), `sync_bars` automatically catches up
all unrecorded trading sessions in strict chronological T+1 order rather than deadlocking.
"""
from __future__ import annotations

import csv
from datetime import date
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from quant_robot.config.settings import PortfolioSpec
from quant_robot.storage.atomic import atomic_write_json, atomic_write_text
from quant_robot.strategies.builtins import compute_target_weights, is_rebalance_day, should_rebalance_by_band

EQUITY_COLUMNS = ["date", "nav", "cash", "market_value", "daily_return", "drawdown", "peak_nav", "trades", "total_fees"]
TRADE_COLUMNS = ["date", "symbol", "side", "quantity", "raw_price", "notional", "commission", "slippage", "reason"]


class PaperLedger:
    """Persistent simulated portfolio ledger with atomic state saves and automatic catch-up."""

    def __init__(self, spec: PortfolioSpec, root_dir: str | Path) -> None:
        self.spec = spec
        self.dir = Path(root_dir) / spec.portfolio_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / "state.json"
        self.equity_path = self.dir / "equity.csv"
        self.trades_path = self.dir / "trades.csv"
        self.signal_path = self.dir / "latest_signal.json"

    def load_state(self) -> dict[str, Any]:
        if self.state_path.is_file():
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        return {
            "portfolio_id": self.spec.portfolio_id,
            "name": self.spec.name,
            "market": self.spec.market,
            "currency": self.spec.currency,
            "paper_only": True,
            "executable": False,
            "initial_cash": float(self.spec.initial_cash),
            "cash": float(self.spec.initial_cash),
            "nav": float(self.spec.initial_cash),
            "market_value": 0.0,
            "peak_nav": float(self.spec.initial_cash),
            "prev_nav": float(self.spec.initial_cash),
            "max_drawdown": 0.0,
            "cooldown_left": 0,
            "total_commission": 0.0,
            "total_slippage": 0.0,
            "trade_count": 0,
            "days_recorded": 0,
            "first_date": None,
            "last_date": None,
            "positions": {},  # symbol -> {"adj_shares": float, "raw_qty": int, "avg_cost": float, "last_price": float, "market_value": float}
            "pending_targets": None,
            "pending_reason": "",
            "updated_at": None,
        }

    def sync_bars(self, bars: pd.DataFrame) -> dict[str, Any]:
        """Advance ledger chronologically across all new trading dates >= start_date. Idempotent."""
        state = self.load_state()
        if bars.empty:
            return {"portfolio_id": self.spec.portfolio_id, "new_days": 0, "status": "no_bars", "state": state}

        df = bars.copy()
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["symbol"] = df["symbol"].astype(str).str.upper()
        norm_symbols = [s.strip().upper() for s in self.spec.symbols]
        df = df[df["symbol"].isin(norm_symbols)].sort_values(["date", "symbol"])
        if df.empty:
            return {"portfolio_id": self.spec.portfolio_id, "new_days": 0, "status": "no_matching_symbols", "state": state}

        adj_panel = df.pivot_table(index="date", columns="symbol", values="adj_close", aggfunc="last").sort_index().ffill()
        raw_close_panel = df.pivot_table(index="date", columns="symbol", values="close", aggfunc="last").sort_index().ffill()
        raw_open_panel = df.pivot_table(index="date", columns="symbol", values="open", aggfunc="last").sort_index().ffill()
        adj_ratio = (adj_panel / raw_close_panel).replace([np.inf, -np.inf], np.nan).ffill().fillna(1.0)
        adj_open_panel = raw_open_panel * adj_ratio

        all_dates = list(adj_panel.index)
        start_d = pd.to_datetime(self.spec.start_date).date()
        last_done = pd.to_datetime(state["last_date"]).date() if state.get("last_date") else None

        pending_indices = [
            i
            for i, d in enumerate(all_dates)
            if d >= start_d and (last_done is None or d > last_done)
        ]
        if not pending_indices:
            return {"portfolio_id": self.spec.portfolio_id, "new_days": 0, "status": "up_to_date", "state": state}

        eq_history = self._load_csv(self.equity_path, EQUITY_COLUMNS)
        tr_history = self._load_csv(self.trades_path, TRADE_COLUMNS)
        exec_panel = adj_open_panel if self.spec.execution_price == "open" else adj_panel
        raw_exec_panel = raw_open_panel if self.spec.execution_price == "open" else raw_close_panel

        new_days = 0
        new_trades = 0
        latest_signal: dict[str, Any] = {}

        for idx in pending_indices:
            cur_date: date = all_dates[idx]
            day_trades = 0
            # 1) Execute pending signal from prior close on today's session (causal T+1)
            if state.get("pending_targets") is not None:
                fills = self._apply_rebalance(
                    state=state,
                    cur_date=cur_date,
                    target_weights=state["pending_targets"],
                    exec_prices=exec_panel.iloc[idx],
                    raw_prices=raw_exec_panel.iloc[idx],
                    reason=str(state.get("pending_reason", "rebalance")),
                )
                for fill in fills:
                    tr_history.append(fill)
                    state["total_commission"] = round(float(state["total_commission"]) + fill["commission"], 4)
                    state["total_slippage"] = round(float(state["total_slippage"]) + fill["slippage"], 4)
                    state["trade_count"] = int(state["trade_count"]) + 1
                day_trades = len(fills)
                new_trades += day_trades
                state["pending_targets"] = None
                state["pending_reason"] = ""

            # 2) Mark-to-market at close
            close_adj = adj_panel.iloc[idx]
            close_raw = raw_close_panel.iloc[idx]
            mv = 0.0
            for sym, pos in list(state["positions"].items()):
                adj_px = close_adj.get(sym)
                raw_px = close_raw.get(sym)
                adj_sh = float(pos["adj_shares"])
                if adj_sh <= 1e-9:
                    state["positions"].pop(sym, None)
                    continue
                if pd.notna(adj_px) and float(adj_px) > 0:
                    val = adj_sh * float(adj_px)
                    pos["last_price"] = round(float(raw_px), 4) if pd.notna(raw_px) else round(float(adj_px), 4)
                    pos["market_value"] = round(val, 2)
                    mv += val
            cash = float(state["cash"])
            nav = cash + mv
            peak_nav = max(float(state["peak_nav"]), nav)
            prev_nav = float(state["prev_nav"])
            dd = (nav / peak_nav - 1.0) if peak_nav > 0 else 0.0
            daily_ret = (nav / prev_nav - 1.0) if prev_nav > 0 else 0.0

            state["nav"] = round(nav, 4)
            state["market_value"] = round(mv, 4)
            state["peak_nav"] = round(peak_nav, 4)
            state["prev_nav"] = round(nav, 4)
            state["max_drawdown"] = round(min(float(state["max_drawdown"]), dd), 6)
            state["days_recorded"] = int(state["days_recorded"]) + 1
            if state["first_date"] is None:
                state["first_date"] = cur_date.isoformat()
            state["last_date"] = cur_date.isoformat()
            state["updated_at"] = pd.Timestamp.now(tz="UTC").isoformat()

            eq_history.append(
                {
                    "date": cur_date.isoformat(),
                    "nav": round(nav, 4),
                    "cash": round(cash, 4),
                    "market_value": round(mv, 4),
                    "daily_return": round(daily_ret, 6),
                    "drawdown": round(dd, 6),
                    "peak_nav": round(peak_nav, 4),
                    "trades": day_trades,
                    "total_fees": round(float(state["total_commission"]) + float(state["total_slippage"]), 4),
                }
            )
            new_days += 1

            # 3) Risk guard + Strategy decision for NEXT session (T+1)
            history = adj_panel.iloc[: idx + 1]
            cur_weights = {
                sym: (float(pos["market_value"]) / nav)
                for sym, pos in state["positions"].items()
                if nav > 0 and float(pos.get("market_value", 0.0)) > 0
            }
            decision_action = "hold"
            diagnostics: dict[str, Any] = {}
            target_weights_preview: dict[str, float] = dict(cur_weights)

            if int(state["cooldown_left"]) > 0:
                state["cooldown_left"] = int(state["cooldown_left"]) - 1
                decision_action = f"cooldown_remaining_{state['cooldown_left']}"
                if state["cooldown_left"] == 0:
                    state["peak_nav"] = round(nav, 4)
            elif self.spec.risk.max_drawdown_halt is not None and (-dd) >= self.spec.risk.max_drawdown_halt and mv > 0:
                state["pending_targets"] = {}
                state["pending_reason"] = f"drawdown_halt_{self.spec.risk.max_drawdown_halt:.0%}"
                state["cooldown_left"] = max(1, self.spec.risk.cooldown_sessions)
                decision_action = state["pending_reason"]
                target_weights_preview = {}
            elif self.spec.risk.daily_loss_halt is not None and (-daily_ret) >= self.spec.risk.daily_loss_halt and mv > 0:
                state["pending_targets"] = {}
                state["pending_reason"] = f"daily_loss_halt_{self.spec.risk.daily_loss_halt:.1%}"
                state["cooldown_left"] = max(1, self.spec.risk.cooldown_sessions)
                decision_action = state["pending_reason"]
                target_weights_preview = {}
            else:
                has_pos = bool(state["positions"])
                if is_rebalance_day(all_dates, idx, self.spec.strategy.rebalance_frequency, has_positions=has_pos):
                    targets, diagnostics = compute_target_weights(history, norm_symbols, self.spec.strategy, self.spec.risk)
                    target_weights_preview = targets
                    if not has_pos or should_rebalance_by_band(cur_weights, targets, self.spec.strategy.rebalance_band):
                        state["pending_targets"] = targets
                        state["pending_reason"] = "initial_entry" if not has_pos else "scheduled_rebalance"
                        decision_action = state["pending_reason"]

            latest_signal = {
                "portfolio_id": self.spec.portfolio_id,
                "asof_date": cur_date.isoformat(),
                "decision_action": decision_action,
                "pending_for_next_session": state["pending_targets"] is not None,
                "current_weights": {k: round(v, 4) for k, v in cur_weights.items()},
                "target_weights": {k: round(v, 4) for k, v in target_weights_preview.items()},
                "diagnostics": diagnostics,
                "paper_only": True,
                "executable": False,
                "safety_note": "Simulated paper-trading plan only. No broker connection or live orders.",
            }

        self._write_csv(self.equity_path, EQUITY_COLUMNS, eq_history)
        self._write_csv(self.trades_path, TRADE_COLUMNS, tr_history)
        atomic_write_json(self.state_path, state)
        if latest_signal:
            atomic_write_json(self.signal_path, latest_signal)

        return {
            "portfolio_id": self.spec.portfolio_id,
            "status": "updated",
            "new_days": new_days,
            "new_trades": new_trades,
            "last_date": state["last_date"],
            "nav": state["nav"],
            "state": state,
        }

    def _apply_rebalance(
        self,
        *,
        state: dict[str, Any],
        cur_date: date,
        target_weights: dict[str, float],
        exec_prices: pd.Series,
        raw_prices: pd.Series,
        reason: str,
    ) -> list[dict[str, Any]]:
        cash = float(state["cash"])
        positions: dict[str, dict[str, Any]] = state["positions"]
        lot_size = int(self.spec.lot_size)
        cost = self.spec.cost

        nav = cash
        for sym, pos in positions.items():
            px = exec_prices.get(sym)
            if pd.notna(px) and float(px) > 0:
                nav += float(pos["adj_shares"]) * float(px)
        if nav <= 0:
            return []

        all_syms = sorted(set(self.spec.symbols) | set(positions.keys()))
        desired: dict[str, float] = {}
        scales: dict[str, float] = {}
        for sym in all_syms:
            adj_px = exec_prices.get(sym)
            raw_px = raw_prices.get(sym)
            cur_adj = float(positions.get(sym, {}).get("adj_shares", 0.0))
            if pd.isna(adj_px) or pd.isna(raw_px) or float(adj_px) <= 0 or float(raw_px) <= 0:
                desired[sym] = cur_adj
                scales[sym] = 1.0
                continue
            scale = float(raw_px) / float(adj_px)
            scales[sym] = scale
            tgt_val = nav * float(target_weights.get(sym, 0.0))
            lots = math.floor(tgt_val / (float(raw_px) * lot_size))
            desired[sym] = lots * lot_size * scale

        fills: list[dict[str, Any]] = []
        # 1) Sells first
        for sym in all_syms:
            cur_adj = float(positions.get(sym, {}).get("adj_shares", 0.0))
            tgt_adj = desired[sym]
            if cur_adj <= 1e-9 or tgt_adj >= cur_adj - 1e-9:
                continue
            adj_px = float(exec_prices[sym])
            raw_px = float(raw_prices[sym])
            scale = max(scales[sym], 1e-12)
            if tgt_adj <= 1e-9:
                sell_adj = cur_adj
                new_adj = 0.0
                raw_qty = max(1, int(positions[sym].get("raw_qty", round(sell_adj / scale))))
            else:
                sell_lots = math.floor(((cur_adj - tgt_adj) / scale + 1e-9) / lot_size)
                if sell_lots <= 0:
                    continue
                raw_qty = int(sell_lots * lot_size)
                sell_adj = min(cur_adj, raw_qty * scale)
                new_adj = max(0.0, cur_adj - sell_adj)

            gross = sell_adj * adj_px
            slip = gross * (cost.slippage_bps / 10000.0)
            comm = max(gross * (cost.commission_bps / 10000.0), cost.minimum_commission)
            duty = gross * (cost.stamp_duty_sell_bps / 10000.0)
            cash += gross - slip - comm - duty
            if new_adj <= 1e-9:
                positions.pop(sym, None)
            else:
                positions[sym]["adj_shares"] = new_adj
                positions[sym]["raw_qty"] = max(0, int(positions[sym].get("raw_qty", 0)) - raw_qty)
            fills.append(
                {
                    "date": cur_date.isoformat(),
                    "symbol": sym,
                    "side": "SELL",
                    "quantity": raw_qty,
                    "raw_price": round(raw_px, 4),
                    "notional": round(gross, 2),
                    "commission": round(comm + duty, 4),
                    "slippage": round(slip, 4),
                    "reason": reason,
                }
            )

        # 2) Buys second
        for sym in all_syms:
            cur_adj = float(positions.get(sym, {}).get("adj_shares", 0.0))
            tgt_adj = desired[sym]
            if tgt_adj <= cur_adj + 1e-9:
                continue
            adj_px = exec_prices.get(sym)
            raw_px = raw_prices.get(sym)
            if pd.isna(adj_px) or pd.isna(raw_px) or float(adj_px) <= 0 or float(raw_px) <= 0:
                continue
            adj_px_f = float(adj_px)
            raw_px_f = float(raw_px)
            scale = scales[sym]
            need_lots = math.floor(((tgt_adj - cur_adj) / scale + 1e-9) / lot_size)
            while need_lots > 0:
                buy_qty = int(need_lots * lot_size)
                buy_adj = buy_qty * scale
                gross = buy_adj * adj_px_f
                slip = gross * (cost.slippage_bps / 10000.0)
                comm = max(gross * (cost.commission_bps / 10000.0), cost.minimum_commission)
                total_out = gross + slip + comm
                if total_out <= cash + 1e-9:
                    cash -= total_out
                    prev = positions.get(sym)
                    if prev:
                        old_qty = int(prev.get("raw_qty", 0))
                        old_cost = float(prev.get("avg_cost", raw_px_f))
                        new_qty = old_qty + buy_qty
                        avg_cost = (old_qty * old_cost + gross) / max(new_qty, 1)
                        positions[sym] = {
                            "adj_shares": cur_adj + buy_adj,
                            "raw_qty": new_qty,
                            "avg_cost": round(avg_cost, 4),
                            "last_price": round(raw_px_f, 4),
                            "market_value": round((cur_adj + buy_adj) * adj_px_f, 2),
                        }
                    else:
                        positions[sym] = {
                            "adj_shares": buy_adj,
                            "raw_qty": buy_qty,
                            "avg_cost": round(raw_px_f, 4),
                            "last_price": round(raw_px_f, 4),
                            "market_value": round(gross, 2),
                        }
                    fills.append(
                        {
                            "date": cur_date.isoformat(),
                            "symbol": sym,
                            "side": "BUY",
                            "quantity": buy_qty,
                            "raw_price": round(raw_px_f, 4),
                            "notional": round(gross, 2),
                            "commission": round(comm, 4),
                            "slippage": round(slip, 4),
                            "reason": reason,
                        }
                    )
                    break
                need_lots -= 1

        state["cash"] = round(cash, 4)
        return fills

    @staticmethod
    def _load_csv(path: Path, columns: list[str]) -> list[dict[str, Any]]:
        if not path.is_file():
            return []
        with path.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    @staticmethod
    def _write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
        lines = [",".join(columns)]
        for row in rows:
            lines.append(",".join(str(row.get(col, "")) for col in columns))
        atomic_write_text(path, "\n".join(lines) + "\n", encoding="utf-8")
