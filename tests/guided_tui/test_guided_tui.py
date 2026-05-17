"""Unit tests for interfaces.guided_tui — picker, questionnaire, and render."""

from __future__ import annotations

from io import StringIO
from pathlib import Path, PurePosixPath
from typing import Any
from unittest.mock import patch

import pytest
from rich.console import Console

from interfaces.guided_tui.picker import pick_preset
from interfaces.guided_tui.questionnaire import (
    _ask_question,
    _parse_boolean,
    _parse_choice,
    _parse_path,
    _parse_text,
    run_questionnaire,
)
from interfaces.guided_tui.render import (
    _get_preset_description,
    _get_preset_name,
    build_preset_table,
    build_summary_table,
    print_error,
    print_header,
    print_info,
    print_panel,
    print_subheader,
    print_success,
    print_warning,
)


@pytest.fixture
def console() -> Console:
    """Return a Console that writes to an in-memory buffer."""
    return Console(file=StringIO(), color_system=None)


@pytest.fixture
def mock_console_input(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Return a helper that patches console.input to consume values sequentially."""

    def _patch(c: Console, values: list[str]) -> None:
        inputs = iter(values)

        def _mock_input(*args: Any, **kwargs: Any) -> str:
            try:
                return next(inputs)
            except StopIteration:
                raise RuntimeError("No more mock inputs available")

        monkeypatch.setattr(c, "input", _mock_input)

    return _patch


# ---------------------------------------------------------------------------
# picker.py
# ---------------------------------------------------------------------------


class TestPickPreset:
    """Tests for pick_preset()."""

    def test_empty_presets_returns_none_and_prints_error(self, console: Console) -> None:
        """Empty presets list returns None and prints an error message."""
        result = pick_preset(console, [])
        assert result is None
        output = console.file.getvalue()
        assert "No presets are available" in output

    def test_valid_number_selection_returns_preset(self, console: Console, mock_console_input: Any) -> None:
        """Selecting a valid number returns the corresponding preset."""
        presets = [
            type("Preset", (), {"id": "alpha"})(),
            type("Preset", (), {"id": "beta"})(),
            type("Preset", (), {"id": "gamma"})(),
        ]
        mock_console_input(console, ["2"])
        result = pick_preset(console, presets)
        assert result.id == "beta"

    def test_out_of_range_then_valid_reprompts(self, console: Console, mock_console_input: Any) -> None:
        """Out-of-range input prints an error and re-prompts until valid."""
        presets = [
            type("Preset", (), {"id": "alpha"})(),
            type("Preset", (), {"id": "beta"})(),
        ]
        mock_console_input(console, ["0", "3", "1"])
        result = pick_preset(console, presets)
        assert result.id == "alpha"
        output = console.file.getvalue()
        assert "between 1 and 2" in output

    def test_non_digit_then_valid_reprompts(self, console: Console, mock_console_input: Any) -> None:
        """Non-digit input prints an error and re-prompts until valid."""
        presets = [type("Preset", (), {"id": "alpha"})()]
        mock_console_input(console, ["abc", "1"])
        result = pick_preset(console, presets)
        assert result.id == "alpha"
        output = console.file.getvalue()
        assert "Please enter a number" in output

    @pytest.mark.parametrize("choice", ["q", "quit", "exit", ""])
    def test_quit_variants_return_none(self, console: Console, mock_console_input: Any, choice: str) -> None:
        """Quit commands and empty input return None immediately."""
        presets = [type("Preset", (), {"id": "alpha"})()]
        mock_console_input(console, [choice])
        result = pick_preset(console, presets)
        assert result is None

    def test_eoferror_returns_none(self, console: Console, monkeypatch: pytest.MonkeyPatch) -> None:
        """EOFError during input returns None."""
        presets = [type("Preset", (), {"id": "alpha"})()]

        def _raise_eof(*args: Any, **kwargs: Any) -> str:
            raise EOFError()

        monkeypatch.setattr(console, "input", _raise_eof)
        result = pick_preset(console, presets)
        assert result is None

    def test_keyboard_interrupt_returns_none(self, console: Console, monkeypatch: pytest.MonkeyPatch) -> None:
        """KeyboardInterrupt during input returns None."""
        presets = [type("Preset", (), {"id": "alpha"})()]

        def _raise_kbd(*args: Any, **kwargs: Any) -> str:
            raise KeyboardInterrupt()

        monkeypatch.setattr(console, "input", _raise_kbd)
        result = pick_preset(console, presets)
        assert result is None


# ---------------------------------------------------------------------------
# questionnaire.py
# ---------------------------------------------------------------------------


class TestRunQuestionnaire:
    """Tests for run_questionnaire()."""

    def test_empty_questions_returns_empty_dict(self, console: Console) -> None:
        """Empty questions list returns empty answers dict and prints warning."""
        result = run_questionnaire(console, [])
        assert result == {}
        output = console.file.getvalue()
        assert "no questions" in output.lower()

    def test_text_question(self, console: Console, mock_console_input: Any) -> None:
        """A simple text question collects the answer."""
        questions = [{"id": "name", "text": "Your name", "type": "text"}]
        mock_console_input(console, ["Alice"])
        result = run_questionnaire(console, questions)
        assert result == {"name": "Alice"}

    def test_multiple_questions(self, console: Console, mock_console_input: Any) -> None:
        """Multiple questions are collected in order."""
        questions = [
            {"id": "q1", "text": "First", "type": "text"},
            {"id": "q2", "text": "Second", "type": "text"},
        ]
        mock_console_input(console, ["a", "b"])
        result = run_questionnaire(console, questions)
        assert result == {"q1": "a", "q2": "b"}


class TestAskQuestion:
    """Tests for _ask_question()."""

    def test_text_default_used_when_empty(self, console: Console, mock_console_input: Any) -> None:
        """Empty input falls back to default for text questions."""
        question = {"id": "q", "text": "Q", "type": "text", "default": "fallback"}
        mock_console_input(console, [""])
        result = _ask_question(console, question)
        assert result == "fallback"

    def test_text_required_reprompts(self, console: Console, mock_console_input: Any) -> None:
        """Required text question re-prompts until a valid answer is given."""
        question = {"id": "q", "text": "Q", "type": "text", "required": True}
        mock_console_input(console, ["", "", "ok"])
        result = _ask_question(console, question)
        assert result == "ok"
        output = console.file.getvalue()
        assert output.count("A valid answer is required") == 2

    def test_text_valid_answer_returned(self, console: Console, mock_console_input: Any) -> None:
        """A non-empty text answer is returned as-is."""
        question = {"id": "q", "text": "Q", "type": "text"}
        mock_console_input(console, ["hello"])
        result = _ask_question(console, question)
        assert result == "hello"

    def test_choice_by_number(self, console: Console, mock_console_input: Any) -> None:
        """Choice question accepts numeric selection."""
        question = {
            "id": "q",
            "text": "Q",
            "type": "choice",
            "choices": ["red", "green", "blue"],
        }
        mock_console_input(console, ["2"])
        result = _ask_question(console, question)
        assert result == "green"

    def test_choice_by_exact_text(self, console: Console, mock_console_input: Any) -> None:
        """Choice question accepts exact text matching an option."""
        question = {
            "id": "q",
            "text": "Q",
            "type": "choice",
            "choices": ["red", "green"],
        }
        mock_console_input(console, ["red"])
        result = _ask_question(console, question)
        assert result == "red"

    def test_choice_default(self, console: Console, mock_console_input: Any) -> None:
        """Choice question falls back to default on empty input."""
        question = {
            "id": "q",
            "text": "Q",
            "type": "choice",
            "choices": ["red", "green"],
            "default": "green",
        }
        mock_console_input(console, [""])
        result = _ask_question(console, question)
        assert result == "green"

    def test_boolean_yes_variants(self, console: Console, mock_console_input: Any) -> None:
        """Boolean variants that should evaluate to True."""
        question = {"id": "q", "text": "Q", "type": "boolean"}
        for val in ["y", "yes", "true", "1", "on"]:
            mock_console_input(console, [val])
            result = _ask_question(console, question)
            assert result is True, f"Expected True for {val!r}"

    def test_boolean_no_variants(self, console: Console, mock_console_input: Any) -> None:
        """Boolean variants that should evaluate to False."""
        question = {"id": "q", "text": "Q", "type": "boolean"}
        for val in ["n", "no", "false", "0", "off"]:
            mock_console_input(console, [val])
            result = _ask_question(console, question)
            assert result is False, f"Expected False for {val!r}"

    def test_boolean_default(self, console: Console, mock_console_input: Any) -> None:
        """Boolean question falls back to default on empty input."""
        question = {"id": "q", "text": "Q", "type": "boolean", "default": True}
        mock_console_input(console, [""])
        result = _ask_question(console, question)
        assert result is True

    def test_path_expands_tilde(self, console: Console, mock_console_input: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        """Path question expands ~ to the user's home directory."""
        monkeypatch.setattr(
            "interfaces.guided_tui.questionnaire.os.path.expanduser",
            lambda p: p.replace("~", "/home/testuser"),
        )
        monkeypatch.setattr(
            "interfaces.guided_tui.questionnaire.os.path.expandvars", lambda p: p
        )
        question = {"id": "q", "text": "Q", "type": "path"}
        mock_console_input(console, ["~/docs"])
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "resolve", return_value=PurePosixPath("/home/testuser/docs")):
                result = _ask_question(console, question)
        assert result == "/home/testuser/docs"

    def test_path_expands_env_vars(self, console: Console, mock_console_input: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        """Path question expands environment variables."""
        monkeypatch.setattr(
            "interfaces.guided_tui.questionnaire.os.path.expandvars",
            lambda p: p.replace("$PROJ", "/projects"),
        )
        monkeypatch.setattr(
            "interfaces.guided_tui.questionnaire.os.path.expanduser", lambda p: p
        )
        question = {"id": "q", "text": "Q", "type": "path"}
        mock_console_input(console, ["$PROJ/src"])
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "resolve", return_value=PurePosixPath("/projects/src")):
                result = _ask_question(console, question)
        assert result == "/projects/src"

    def test_path_default(self, console: Console, mock_console_input: Any) -> None:
        """Path question falls back to default on empty input."""
        question = {"id": "q", "text": "Q", "type": "path", "default": "/default/path"}
        mock_console_input(console, [""])
        result = _ask_question(console, question)
        assert result == "/default/path"

    def test_optional_empty_answer_returns_empty_string(self, console: Console, mock_console_input: Any) -> None:
        """Optional question with empty input returns empty string."""
        question = {"id": "q", "text": "Q", "type": "text", "required": False}
        mock_console_input(console, [""])
        result = _ask_question(console, question)
        assert result == ""


class TestParseText:
    """Tests for _parse_text()."""

    def test_empty_with_default(self) -> None:
        """Empty raw value with a defined default returns the default."""
        assert _parse_text("", "def", True) == "def"

    def test_empty_without_default_optional(self) -> None:
        """Empty raw value without default and optional returns empty string."""
        assert _parse_text("", None, False) == ""

    def test_empty_without_default_required(self) -> None:
        """Empty raw value without default and required returns None."""
        assert _parse_text("", None, True) is None

    def test_non_empty_returned(self) -> None:
        """Non-empty raw value is returned unchanged."""
        assert _parse_text("hello", None, True) == "hello"


class TestParseChoice:
    """Tests for _parse_choice()."""

    def test_empty_with_default(self) -> None:
        """Empty input with default returns the default choice."""
        assert _parse_choice("", ["a", "b"], "a", True) == "a"

    def test_empty_without_default_optional(self) -> None:
        """Empty input without default and optional returns empty string."""
        assert _parse_choice("", ["a", "b"], None, False) == ""

    def test_empty_without_default_required(self) -> None:
        """Empty input without default and required returns None."""
        assert _parse_choice("", ["a", "b"], None, True) is None

    def test_by_number(self) -> None:
        """Numeric input selects the corresponding choice."""
        assert _parse_choice("2", ["a", "b", "c"], None, True) == "b"

    def test_by_exact_text(self) -> None:
        """Exact text matching a choice returns that choice."""
        assert _parse_choice("b", ["a", "b", "c"], None, True) == "b"

    def test_out_of_range_returns_none(self) -> None:
        """Out-of-range number returns None."""
        assert _parse_choice("5", ["a", "b"], None, True) is None

    def test_invalid_text_returns_none(self) -> None:
        """Text not matching any choice returns None."""
        assert _parse_choice("z", ["a", "b"], None, True) is None


class TestParseBoolean:
    """Tests for _parse_boolean()."""

    @pytest.mark.parametrize("val", ["y", "yes", "true", "1", "on"])
    def test_true_variants(self, val: str) -> None:
        """Affirmative inputs evaluate to True."""
        assert _parse_boolean(val, None, True) is True

    @pytest.mark.parametrize("val", ["n", "no", "false", "0", "off"])
    def test_false_variants(self, val: str) -> None:
        """Negative inputs evaluate to False."""
        assert _parse_boolean(val, None, True) is False

    def test_empty_with_default(self) -> None:
        """Empty input with default returns the default boolean."""
        assert _parse_boolean("", False, True) is False

    def test_empty_without_default(self) -> None:
        """Empty input without default returns None."""
        assert _parse_boolean("", None, True) is None

    def test_invalid_returns_none(self) -> None:
        """Invalid boolean input returns None."""
        assert _parse_boolean("maybe", None, True) is None


class TestParsePath:
    """Tests for _parse_path()."""

    def test_empty_with_default(self, console: Console) -> None:
        """Empty input with default returns the default path."""
        assert _parse_path(console, "", "/default", True) == "/default"

    def test_empty_without_default_optional(self, console: Console) -> None:
        """Empty input without default and optional returns empty string."""
        assert _parse_path(console, "", None, False) == ""

    def test_empty_without_default_required(self, console: Console) -> None:
        """Empty input without default and required returns None."""
        assert _parse_path(console, "", None, True) is None

    def test_missing_path_returns_none(self, console: Console, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-existent path prints an error and returns None."""
        monkeypatch.setattr(
            "interfaces.guided_tui.questionnaire.os.path.expanduser", lambda p: p
        )
        monkeypatch.setattr(
            "interfaces.guided_tui.questionnaire.os.path.expandvars", lambda p: p
        )
        with patch.object(Path, "exists", return_value=False):
            result = _parse_path(console, "/missing", None, True)
        assert result is None
        output = console.file.getvalue()
        assert "Path does not exist" in output

    def test_valid_path_expanded_and_resolved(self, console: Console, monkeypatch: pytest.MonkeyPatch) -> None:
        """Existing path is expanded and resolved to an absolute path."""
        monkeypatch.setattr(
            "interfaces.guided_tui.questionnaire.os.path.expanduser", lambda p: p
        )
        monkeypatch.setattr(
            "interfaces.guided_tui.questionnaire.os.path.expandvars", lambda p: p
        )
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "resolve", return_value=PurePosixPath("/resolved")):
                result = _parse_path(console, "/some/path", None, True)
        assert result == "/resolved"


# ---------------------------------------------------------------------------
# render.py
# ---------------------------------------------------------------------------


class TestPrintHelpers:
    """Tests for rendering helpers."""

    def test_print_header(self, console: Console) -> None:
        """print_header outputs the title."""
        print_header(console, "Title")
        output = console.file.getvalue()
        assert "Title" in output

    def test_print_subheader(self, console: Console) -> None:
        """print_subheader outputs the title."""
        print_subheader(console, "Sub")
        output = console.file.getvalue()
        assert "Sub" in output

    def test_print_info(self, console: Console) -> None:
        """print_info outputs the message."""
        print_info(console, "info msg")
        output = console.file.getvalue()
        assert "info msg" in output

    def test_print_success(self, console: Console) -> None:
        """print_success outputs a check mark and the message."""
        print_success(console, "done")
        output = console.file.getvalue()
        assert "done" in output
        assert "✓" in output

    def test_print_error(self, console: Console) -> None:
        """print_error outputs an X and the message."""
        print_error(console, "fail")
        output = console.file.getvalue()
        assert "fail" in output
        assert "✗" in output

    def test_print_warning(self, console: Console) -> None:
        """print_warning outputs a warning sign and the message."""
        print_warning(console, "warn")
        output = console.file.getvalue()
        assert "warn" in output
        assert "⚠" in output

    def test_print_panel(self, console: Console) -> None:
        """print_panel outputs the title and content inside a panel."""
        print_panel(console, "PanelTitle", "content here")
        output = console.file.getvalue()
        assert "PanelTitle" in output
        assert "content here" in output


class TestBuildPresetTable:
    """Tests for build_preset_table()."""

    def test_columns_and_numbering(self, console: Console) -> None:
        """Table includes correct columns, numbering, name, and description."""
        presets = [
            type("Obj", (), {"metadata": {"name": "A", "description": "Desc A"}})(),
            type("Obj", (), {"name": "B", "description": "Desc B"})(),
        ]
        table = build_preset_table(presets)
        console.print(table)
        output = console.file.getvalue()
        assert "#" in output
        assert "Name" in output
        assert "Description" in output
        assert "1" in output
        assert "2" in output
        assert "A" in output
        assert "B" in output
        assert "Desc A" in output
        assert "Desc B" in output


class TestBuildSummaryTable:
    """Tests for build_summary_table()."""

    def test_rows(self, console: Console) -> None:
        """Table renders question IDs and answers as rows."""
        answers = {"q1": "a1", "q2": "a2"}
        table = build_summary_table(answers)
        console.print(table)
        output = console.file.getvalue()
        assert "Question" in output
        assert "Answer" in output
        assert "q1" in output
        assert "a1" in output
        assert "q2" in output
        assert "a2" in output


class TestGetPresetName:
    """Tests for _get_preset_name() fallback chain."""

    def test_metadata_name(self) -> None:
        """Name is extracted from metadata.name when available."""
        preset = type("P", (), {"metadata": {"name": "MetaName"}})()
        assert _get_preset_name(preset) == "MetaName"

    def test_name_attr(self) -> None:
        """Name falls back to the name attribute."""
        preset = type("P", (), {"name": "NameAttr"})()
        assert _get_preset_name(preset) == "NameAttr"

    def test_preset_id_attr(self) -> None:
        """Name falls back to preset_id attribute."""
        preset = type("P", (), {"preset_id": "PID"})()
        assert _get_preset_name(preset) == "PID"

    def test_id_attr(self) -> None:
        """Name falls back to id attribute."""
        preset = type("P", (), {"id": "ID"})()
        assert _get_preset_name(preset) == "ID"


class TestGetPresetDescription:
    """Tests for _get_preset_description() fallback chain."""

    def test_metadata_description(self) -> None:
        """Description is extracted from metadata.description when available."""
        preset = type("P", (), {"metadata": {"description": "MetaDesc"}})()
        assert _get_preset_description(preset) == "MetaDesc"

    def test_description_attr(self) -> None:
        """Description falls back to the description attribute."""
        preset = type("P", (), {"description": "DescAttr"})()
        assert _get_preset_description(preset) == "DescAttr"

    def test_fallback(self) -> None:
        """Description falls back to the default message."""
        preset = type("P", (), {})()
        assert _get_preset_description(preset) == "No description provided."
