from __future__ import annotations

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

    def test_create_tray_icon(self) -> None:
        from interfaces.desktop_ui.app import _create_tray_icon

        mock_window = MagicMock()
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
        assert "--port" in result.output
        assert "--no-tray" in result.output
