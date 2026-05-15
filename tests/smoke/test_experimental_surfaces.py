"""Regression tests ensuring experimental surfaces are not shown as stable."""

from __future__ import annotations

import pytest


class TestPresetRegistryNoExperimental:
    def test_all_presets_have_support_state(self) -> None:
        from presets import PRESET_REGISTRY

        for preset in PRESET_REGISTRY.list():
            state = getattr(preset, "support_state", None)
            assert state is not None, f"Preset '{preset.preset_id}' missing support_state"

    def test_no_experimental_presets(self) -> None:
        from presets import PRESET_REGISTRY

        for preset in PRESET_REGISTRY.list():
            state = getattr(preset, "support_state", "")
            assert state != "experimental", (
                f"Preset '{preset.preset_id}' is experimental and should not be in stable registry"
            )


class TestWorkflowRegistryNoExperimental:
    def test_all_workflows_have_support_state(self) -> None:
        from workflows.registry import BUILTIN_WORKFLOWS

        for cls in BUILTIN_WORKFLOWS:
            assert hasattr(cls, "support_state"), f"Workflow '{cls.workflow_id}' missing support_state"

    def test_no_experimental_workflows(self) -> None:
        from workflows.registry import BUILTIN_WORKFLOWS

        for cls in BUILTIN_WORKFLOWS:
            assert cls.support_state != "experimental", (
                f"Workflow '{cls.workflow_id}' is experimental and should not be in stable registry"
            )


class TestCliNoExperimentalCommands:
    def test_no_marketplace_or_federation_commands(self) -> None:
        from interfaces.cli.cli import app

        names = []
        for cmd in app.registered_commands:
            names.append(cmd.name)
        for group in app.registered_groups:
            names.append(group.name)
            for cmd in group.typer_instance.registered_commands:
                names.append(group.name + " " + cmd.name)

        blocked = {"marketplace", "federation", "distributed", "multimodal", "self-improving"}
        for name in names:
            for token in blocked:
                assert token not in name, (
                    f"CLI command '{name}' contains experimental token '{token}'"
                )


class TestApiServerNoExperimentalRoutes:
    def test_no_marketplace_or_federation_routes(self) -> None:
        from interfaces.api_server.app import create_api_app
        from pathlib import Path

        app = create_api_app(repo_root=Path("."))
        blocked = {"marketplace", "federation", "distributed", "multimodal", "self-improving"}

        for route in app.routes:
            path = getattr(route, "path", "")
            for token in blocked:
                assert token not in path, (
                    f"API route '{path}' contains experimental token '{token}'"
                )


class TestProviderTemplatesNoExperimentalInFirstRun:
    def test_cli_templates_excludes_experimental_by_default(self) -> None:
        from config.config import list_provider_templates

        templates = list_provider_templates()
        for t in templates:
            assert t["support_state"] != "experimental", (
                f"experimental template '{t['kind']}' in default list_provider_templates()"
            )

    def test_all_templates_have_support_state(self) -> None:
        from config.config import list_provider_templates

        templates = list_provider_templates(include_experimental=True)
        for t in templates:
            assert "support_state" in t, f"template '{t['kind']}' missing support_state"
