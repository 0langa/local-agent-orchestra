"""Desktop UI with pywebview primary, tkinter fallback, browser last resort."""

from __future__ import annotations

import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

from interfaces.web_ui import create_app as create_web_app


def _wait_for_server(port: int, timeout: float = 15.0) -> bool:
    """Poll localhost:port until the health endpoint responds."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/health", timeout=1
            ):
                return True
        except Exception:
            time.sleep(0.2)
    return False


def _run_server(repo_root: Path, port: int) -> None:
    """Run the FastAPI server in a background thread."""
    import uvicorn

    app = create_web_app(repo_root=repo_root)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def _create_tray_icon(window: Any, port: int) -> Any:
    """Create a pystray system-tray icon with Show / Browser / Quit menu."""
    from pystray import Icon, Menu, MenuItem
    from PIL import Image, ImageDraw

    # Generate a simple green-circle icon
    size = 64
    image = Image.new("RGB", (size, size), color="white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, size, size], fill="#2d2d2d")
    draw.ellipse([8, 8, size - 8, size - 8], fill="#4CAF50")

    def show_window() -> None:
        try:
            window.show()
            window.restore()
        except Exception:
            pass

    def open_browser() -> None:
        webbrowser.open(f"http://127.0.0.1:{port}")

    def quit_app() -> None:
        try:
            window.destroy()
        except Exception:
            pass

    menu = Menu(
        MenuItem("Show", show_window),
        MenuItem("Open in Browser", open_browser),
        MenuItem("Quit", quit_app),
    )
    return Icon("Agentheim", image, menu=menu)


def _run_pywebview(repo_root: Path, port: int, use_tray: bool = True) -> None:
    """Run the desktop app using pywebview."""
    import webview

    window = webview.create_window(
        "Agentheim",
        f"http://127.0.0.1:{port}",
        width=1280,
        height=800,
        min_size=(800, 600),
    )

    if use_tray:
        try:
            icon = _create_tray_icon(window, port)
            tray_thread = threading.Thread(target=icon.run, daemon=True)
            tray_thread.start()
        except Exception:
            pass  # tray is optional

    webview.start()


def _run_tkinter(repo_root: Path, port: int) -> None:
    """Run a minimal tkinter desktop wrapper."""
    import tkinter as tk

    root = tk.Tk()
    root.title("Agentheim")
    root.geometry("800x600")

    tk.Label(root, text="Agentheim", font=("Helvetica", 20)).pack(pady=20)
    tk.Label(
        root,
        text=f"Server running at http://127.0.0.1:{port}",
        font=("Helvetica", 12),
    ).pack(pady=10)

    def open_browser() -> None:
        webbrowser.open(f"http://127.0.0.1:{port}")

    tk.Button(
        root, text="Open in Browser", command=open_browser, font=("Helvetica", 14)
    ).pack(pady=20)
    tk.Button(root, text="Exit", command=root.destroy, font=("Helvetica", 14)).pack(
        pady=10
    )

    root.mainloop()


def run_desktop_app(
    repo_root: str | Path = ".",
    port: int = 8765,
    use_tray: bool = True,
    _blocking_fallback: bool = True,
) -> None:
    """Launch the desktop UI, choosing the best available framework."""
    repo_root = Path(repo_root).resolve()

    # Start server in background thread
    server_thread = threading.Thread(
        target=_run_server, args=(repo_root, port), daemon=True
    )
    server_thread.start()

    # Wait for server to be ready
    if not _wait_for_server(port, timeout=15.0):
        print(f"Server failed to start on port {port}. Opening browser fallback.")
        webbrowser.open(f"http://127.0.0.1:{port}")
        return

    # Try pywebview first
    try:
        import webview  # noqa: F401

        _run_pywebview(repo_root, port, use_tray=use_tray)
        return
    except ImportError:
        pass

    # Fallback to tkinter (usually available)
    try:
        import tkinter  # noqa: F401

        _run_tkinter(repo_root, port)
        return
    except ImportError:
        pass

    # Last resort: just open browser
    print(f"No GUI framework available. Opening browser at http://127.0.0.1:{port}")
    webbrowser.open(f"http://127.0.0.1:{port}")
    if _blocking_fallback:
        print("Press Ctrl+C to stop the server.")
        try:
            while True:
                pass
        except KeyboardInterrupt:
            pass
