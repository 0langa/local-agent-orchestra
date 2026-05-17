from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestDesktopUI:
    def test_import(self) -> None:
        from interfaces.desktop_ui import run_desktop_app

        assert callable(run_desktop_app)

    def test_wait_for_server_success(self) -> None:
        from interfaces.desktop_ui.app import _wait_for_server

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock(
                return_value=MagicMock()
            )
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            assert _wait_for_server(9999, timeout=1.0) is True

    def test_wait_for_server_timeout(self) -> None:
        from interfaces.desktop_ui.app import _wait_for_server

        with patch("urllib.request.urlopen", side_effect=Exception("refused")):
            assert _wait_for_server(9999, timeout=0.5) is False

    def test_run_desktop_app_browser_fallback_on_server_timeout(self) -> None:
        from interfaces.desktop_ui.app import run_desktop_app

        with (
            patch("interfaces.desktop_ui.app._run_server"),
            patch(
                "interfaces.desktop_ui.app._wait_for_server", return_value=False
            ) as mock_wait,
            patch("webbrowser.open") as mock_browser,
        ):
            run_desktop_app(port=19999, _blocking_fallback=False)
            mock_wait.assert_called_once()
            mock_browser.assert_called_once_with("http://127.0.0.1:19999")

    def test_run_desktop_app_pywebview_path(self) -> None:
        from interfaces.desktop_ui.app import run_desktop_app

        with (
            patch("interfaces.desktop_ui.app._run_server"),
            patch(
                "interfaces.desktop_ui.app._wait_for_server", return_value=True
            ),
            patch(
                "interfaces.desktop_ui.app._run_pywebview"
            ) as mock_pywebview,
            patch.dict("sys.modules", {"webview": MagicMock()}),
        ):
            run_desktop_app(port=19999, use_tray=False, _blocking_fallback=False)
            mock_pywebview.assert_called_once()

    def test_run_desktop_app_tkinter_fallback(self) -> None:
        from interfaces.desktop_ui.app import run_desktop_app

        fake_tkinter = MagicMock()
        with (
            patch("interfaces.desktop_ui.app._run_server"),
            patch(
                "interfaces.desktop_ui.app._wait_for_server", return_value=True
            ),
            patch(
                "interfaces.desktop_ui.app._run_pywebview",
                side_effect=ImportError("no webview"),
            ),
            patch(
                "interfaces.desktop_ui.app._run_tkinter"
            ) as mock_tkinter,
            patch.dict("sys.modules", {"tkinter": fake_tkinter}),
        ):
            run_desktop_app(port=19999, _blocking_fallback=False)
            mock_tkinter.assert_called_once()

    def test_run_desktop_app_browser_last_resort(self) -> None:
        from interfaces.desktop_ui.app import run_desktop_app

        with (
            patch("interfaces.desktop_ui.app._run_server"),
            patch(
                "interfaces.desktop_ui.app._wait_for_server", return_value=True
            ),
            patch(
                "interfaces.desktop_ui.app._run_pywebview",
                side_effect=ImportError("no webview"),
            ),
            patch(
                "interfaces.desktop_ui.app._run_tkinter",
                side_effect=ImportError("no tkinter"),
            ),
            patch("webbrowser.open") as mock_browser,
        ):
            run_desktop_app(port=19999, _blocking_fallback=False)
            mock_browser.assert_called_once_with("http://127.0.0.1:19999")

    def test_run_desktop_app_browser_last_resort_blocks_with_sleep(self) -> None:
        from interfaces.desktop_ui.app import run_desktop_app

        with (
            patch("interfaces.desktop_ui.app._run_server"),
            patch(
                "interfaces.desktop_ui.app._wait_for_server", return_value=True
            ),
            patch(
                "interfaces.desktop_ui.app._run_pywebview",
                side_effect=ImportError("no webview"),
            ),
            patch(
                "interfaces.desktop_ui.app._run_tkinter",
                side_effect=ImportError("no tkinter"),
            ),
            patch("webbrowser.open"),
            patch("interfaces.desktop_ui.app.time.sleep", side_effect=KeyboardInterrupt) as mock_sleep,
        ):
            run_desktop_app(port=19999, _blocking_fallback=True)
            mock_sleep.assert_called_once_with(1)

    def test_create_tray_icon(self) -> None:
        from interfaces.desktop_ui.app import _create_tray_icon

        class FakeIcon:
            def __init__(self, name, image, menu=None) -> None:
                self.name = name
                self.image = image
                self.menu = menu

        fake_pystray = MagicMock()
        fake_pystray.Icon = FakeIcon
        fake_pystray.Menu = lambda *items: items
        fake_pystray.MenuItem = lambda label, action: (label, action)
        fake_image = MagicMock()
        fake_image.new.return_value = object()
        fake_draw = MagicMock()
        fake_draw.Draw.return_value = MagicMock()
        fake_pil = MagicMock(Image=fake_image, ImageDraw=fake_draw)

        mock_window = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "pystray": fake_pystray,
                "PIL": fake_pil,
                "PIL.Image": fake_image,
                "PIL.ImageDraw": fake_draw,
            },
        ):
            icon = _create_tray_icon(mock_window, port=8765)
        assert icon is not None
        assert icon.name == "Agentheim"

    def test_cli_command_registered(self) -> None:
        from typer.testing import CliRunner
        from interfaces.cli.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["desktop", "--help"])
        assert result.exit_code == 0
        assert "Launch the Agentheim desktop UI" in result.output
        assert "usage:" in result.output.lower()


class TestDesktopUIServerIntegration:
    def test_server_starts_and_health_responds(self, tmp_path: Path) -> None:
        from interfaces.desktop_ui.app import _run_server, _wait_for_server

        port = 18765
        server_thread = threading.Thread(
            target=_run_server, args=(tmp_path, port), daemon=True
        )
        server_thread.start()

        reached = _wait_for_server(port, timeout=10.0)
        assert reached is True, "Desktop UI server did not start within timeout"

        import urllib.request
        import json

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health") as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "ok"

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/presets") as resp:
            presets = json.loads(resp.read().decode("utf-8"))
            assert isinstance(presets, list)
            assert len(presets) > 0
