from __future__ import annotations

import argparse
import json
import re
import socket
import threading
import webbrowser
from dataclasses import dataclass
from typing import Callable, Protocol

from quant_robot.gui.app import create_server


DESKTOP_APP_COPY = {
    "title": "量化机器人新手桌面中控台",
    "subtitle": "一键打开本地研究、信号、模拟盘和手工交易建议。",
    "safety": "research-to-paper only；不连接券商、不读取账户、不真实下单。",
    "primary_button": "启动并打开中控台",
    "today_action_button": "打开今日行动",
    "daily_button": "打开今日交易检查",
    "leaderboard_button": "打开因子排行榜",
    "logs_button": "打开日志报告",
    "stop_button": "停止本地服务",
}
DEFAULT_INITIAL_PAGE = "dashboard"
DEFAULT_INITIAL_TARGET_ID = "ordinary-daily-action-card"

DESKTOP_APP_PAGES = {
    "dashboard",
    "research",
    "backtest",
    "decision",
    "signals",
    "paper",
    "daily",
    "promotion",
    "data",
    "logs",
}
TARGET_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class ServerLike(Protocol):
    def serve_forever(self) -> None: ...

    def shutdown(self) -> None: ...

    def server_close(self) -> None: ...


ServerFactory = Callable[[str, int], ServerLike]
BrowserOpen = Callable[[str], object]


@dataclass(frozen=True)
class DesktopAppState:
    status: str
    host: str
    port: int
    url: str
    message: str
    safety_text: str = DESKTOP_APP_COPY["safety"]


def find_available_port(host: str = "127.0.0.1", start_port: int = 8765, scan_limit: int = 20) -> int:
    for port in range(int(start_port), int(start_port) + max(1, int(scan_limit))):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((host, port)) != 0:
                return port
    raise OSError(f"No free local port found from {start_port} within {scan_limit} attempts")


class DesktopGuiController:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        port_scan_limit: int = 20,
        server_factory: ServerFactory = create_server,
        browser_open: BrowserOpen = webbrowser.open,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.port_scan_limit = int(port_scan_limit)
        self.server_factory = server_factory
        self.browser_open = browser_open
        self.server: ServerLike | None = None
        self.thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    def url_for_page(self, page: str, target_id: str = "") -> str:
        page_id = str(page or "").strip().lower()
        if page_id not in DESKTOP_APP_PAGES:
            return self.url
        target = str(target_id or "").strip()
        if target and TARGET_ID_PATTERN.fullmatch(target):
            return f"{self.url}#{page_id}:{target}"
        if page_id != "dashboard":
            return f"{self.url}#{page_id}"
        return self.url

    def start(self) -> DesktopAppState:
        if self.server is not None:
            return self._state("running", "本地中控台已在运行。")

        last_error: OSError | None = None
        for candidate_port in range(self.port, self.port + max(1, self.port_scan_limit)):
            try:
                server = self.server_factory(self.host, candidate_port)
            except OSError as exc:
                last_error = exc
                continue
            self.port = candidate_port
            self.server = server
            self.thread = threading.Thread(target=server.serve_forever, daemon=True)
            self.thread.start()
            return self._state("running", "本地中控台已启动。")

        raise OSError(f"Unable to start GUI server: {last_error}") from last_error

    def open_console(self) -> DesktopAppState:
        state = self.start()
        self.browser_open(state.url)
        return state

    def open_section(self, page: str, target_id: str = "") -> DesktopAppState:
        state = self.start()
        section_url = self.url_for_page(page, target_id)
        self.browser_open(section_url)
        return DesktopAppState(
            status=state.status,
            host=state.host,
            port=state.port,
            url=section_url,
            message=state.message,
            safety_text=state.safety_text,
        )

    def stop(self) -> DesktopAppState:
        if self.server is None:
            return self._state("stopped", "本地中控台没有运行。")
        server = self.server
        self.server = None
        server.shutdown()
        server.server_close()
        return self._state("stopped", "本地中控台已停止。")

    def _state(self, status: str, message: str) -> DesktopAppState:
        return DesktopAppState(status=status, host=self.host, port=self.port, url=self.url, message=message)


def run_desktop_app(
    host: str = "127.0.0.1",
    port: int = 8765,
    open_on_start: bool = True,
    initial_page: str = DEFAULT_INITIAL_PAGE,
    initial_target_id: str = DEFAULT_INITIAL_TARGET_ID,
) -> DesktopAppState:
    controller = DesktopGuiController(host=host, port=port)
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        state = controller.open_section(initial_page, initial_target_id) if open_on_start else controller.start()
        print(json.dumps(state.__dict__, ensure_ascii=False, indent=2))
        return state

    root = tk.Tk()
    root.title(DESKTOP_APP_COPY["title"])
    root.geometry("560x330")
    root.resizable(False, False)

    status_var = tk.StringVar(value="未启动")
    url_var = tk.StringVar(value=f"http://{host}:{port}/")
    safety_var = tk.StringVar(value=DESKTOP_APP_COPY["safety"])

    frame = ttk.Frame(root, padding=20)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text=DESKTOP_APP_COPY["title"], font=("", 16, "bold")).pack(anchor="w")
    ttk.Label(frame, text=DESKTOP_APP_COPY["subtitle"], wraplength=460).pack(anchor="w", pady=(8, 12))
    ttk.Label(frame, textvariable=safety_var, foreground="#ad3f3c", wraplength=460).pack(anchor="w")
    ttk.Label(frame, textvariable=status_var).pack(anchor="w", pady=(12, 4))
    ttk.Label(frame, textvariable=url_var).pack(anchor="w")

    buttons = ttk.Frame(frame)
    buttons.pack(anchor="w", pady=(16, 0))

    def start_and_open() -> None:
        state = controller.open_console()
        status_var.set(f"{state.message} {state.url}")
        url_var.set(state.url)

    def open_section(page: str, target_id: str = "") -> None:
        state = controller.open_section(page, target_id)
        status_var.set(f"{state.message} {state.url}")
        url_var.set(state.url)

    def stop() -> None:
        state = controller.stop()
        status_var.set(state.message)

    ttk.Button(buttons, text=DESKTOP_APP_COPY["primary_button"], command=start_and_open).pack(side="left")
    ttk.Button(buttons, text=DESKTOP_APP_COPY["stop_button"], command=stop).pack(side="left", padx=(10, 0))

    quick_buttons = ttk.Frame(frame)
    quick_buttons.pack(anchor="w", pady=(12, 0))
    ttk.Button(quick_buttons, text=DESKTOP_APP_COPY["today_action_button"], command=lambda: open_section("dashboard", DEFAULT_INITIAL_TARGET_ID)).pack(side="left")
    ttk.Button(quick_buttons, text=DESKTOP_APP_COPY["daily_button"], command=lambda: open_section("daily")).pack(side="left", padx=(10, 0))
    ttk.Button(quick_buttons, text=DESKTOP_APP_COPY["leaderboard_button"], command=lambda: open_section("dashboard", "factor-leaderboard-table")).pack(side="left", padx=(10, 0))
    ttk.Button(quick_buttons, text=DESKTOP_APP_COPY["logs_button"], command=lambda: open_section("logs")).pack(side="left", padx=(10, 0))

    def on_close() -> None:
        controller.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    state = controller.open_section(initial_page, initial_target_id) if open_on_start else controller._state("stopped", "等待手动启动。")
    status_var.set(f"{state.message} {state.url}" if state.status == "running" else state.message)
    url_var.set(state.url)
    root.mainloop()
    return state


def main(argv: list[str] | None = None, runner: Callable[..., DesktopAppState] = run_desktop_app) -> DesktopAppState:
    parser = argparse.ArgumentParser(description="Run the beginner desktop shell for the local Quant Robot GUI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--no-open", action="store_true", help="Start the desktop shell without opening the browser immediately.")
    parser.add_argument("--page", choices=sorted(DESKTOP_APP_PAGES), default=DEFAULT_INITIAL_PAGE, help="Open a beginner workflow page after starting.")
    parser.add_argument("--target-id", default=None, help="Optional on-page target id to scroll to after opening the page.")
    args = parser.parse_args(argv)
    target_id = args.target_id
    if target_id is None:
        target_id = DEFAULT_INITIAL_TARGET_ID if args.page == DEFAULT_INITIAL_PAGE else ""
    return runner(
        host=args.host,
        port=args.port,
        open_on_start=not args.no_open,
        initial_page=args.page,
        initial_target_id=target_id,
    )


if __name__ == "__main__":
    main()
