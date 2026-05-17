from __future__ import annotations

import json
from pathlib import Path

import pytest

from marketplace import PluginManager, PluginManifest
from marketplace.sandbox import PluginSandboxError, Sandbox


class TestPluginManifest:
    def test_valid_manifest(self) -> None:
        m = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            entry_point="plugin.py",
            author="test",
        )
        ok, err = m.validate()
        assert ok is True
        assert err == ""

    def test_invalid_name(self) -> None:
        m = PluginManifest(name="", version="1.0.0", entry_point="plugin.py", author="test")
        ok, err = m.validate()
        assert ok is False
        assert "name" in err.lower()

    def test_missing_version(self) -> None:
        m = PluginManifest(name="plugin", version="", entry_point="plugin.py", author="test")
        ok, err = m.validate()
        assert ok is False
        assert "version" in err.lower()

    def test_roundtrip_json(self) -> None:
        m = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            entry_point="plugin.py",
            author="test",
            description="A test plugin",
        )
        data = m.to_json()
        restored = PluginManifest.from_json(data)
        assert restored.name == "test-plugin"
        assert restored.description == "A test plugin"

    def test_from_file(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(
            json.dumps({
                "name": "file-plugin",
                "version": "1.0.0",
                "entry_point": "plugin.py",
                "author": "test",
            }),
            encoding="utf-8",
        )
        m = PluginManifest.from_file(manifest_path)
        assert m.name == "file-plugin"


class TestPluginManager:
    """Tests for PluginManager with Ed25519 signature verification."""

    @staticmethod
    def _make_signed_plugin(
        plugin_dir: Path, key_dir: Path, name: str = "my-plugin",
        trusted_key_dir_override: Path | None = None,
    ) -> None:
        """Helper: create a signed plugin at *plugin_dir* using a key in *key_dir*."""
        plugin_dir.mkdir(parents=True, exist_ok=True)
        (plugin_dir / "plugin.py").write_text("x = 42\n", encoding="utf-8")
        from marketplace.signing import PluginSigner
        PluginSigner.generate_keypair(name, key_dir)
        (plugin_dir / "manifest.json").write_text(
            json.dumps({
                "name": name,
                "version": "1.0.0",
                "entry_point": "plugin.py",
                "author": "test",
                "trusted_key_id": name,
            }),
            encoding="utf-8",
        )
        PluginSigner.sign_package(plugin_dir, key_dir / name)
        if trusted_key_dir_override:
            target = trusted_key_dir_override
        else:
            target = plugin_dir.parent.parent / ".agentheim" / "trusted-keys"
        target.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(key_dir / f"{name}.pub", target / f"{name}.pub")

    def _make_mgr(self, tmp_path: Path, *extra_dirs: Path) -> PluginManager:
        """Create a PluginManager with deterministic trusted key dirs."""
        trusted = tmp_path / ".agentheim" / "trusted-keys"
        trusted.mkdir(parents=True, exist_ok=True)
        return PluginManager(
            scan_paths=[tmp_path / "plugins"],
            trusted_key_dirs=[trusted, *extra_dirs],
        )

    def test_discover_finds_manifests(self, tmp_path: Path) -> None:
        key_dir = tmp_path / "keys"
        key_dir.mkdir(parents=True)
        plugin_dir = tmp_path / "plugins" / "my-plugin"
        self._make_signed_plugin(plugin_dir, key_dir, trusted_key_dir_override=tmp_path / ".agentheim" / "trusted-keys")
        mgr = self._make_mgr(tmp_path)
        found = mgr.discover()
        assert len(found) == 1
        assert found[0].name == "my-plugin"

    def test_load_success(self, tmp_path: Path) -> None:
        key_dir = tmp_path / "keys"
        key_dir.mkdir(parents=True)
        plugin_dir = tmp_path / "plugins" / "my-plugin"
        self._make_signed_plugin(plugin_dir, key_dir, trusted_key_dir_override=tmp_path / ".agentheim" / "trusted-keys")
        mgr = self._make_mgr(tmp_path)
        ok, err = mgr.load(plugin_dir)
        assert ok is True, f"Expected success, got: {err}"
        assert err == ""
        assert "my-plugin" in mgr.list_loaded()

    def test_load_rejects_unsigned_plugin(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "plugins" / "unsigned-plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "manifest.json").write_text(
            json.dumps({
                "name": "unsigned-plugin",
                "version": "1.0.0",
                "entry_point": "plugin.py",
                "author": "test",
            }),
            encoding="utf-8",
        )
        (plugin_dir / "plugin.py").write_text("x = 42\n", encoding="utf-8")
        mgr = self._make_mgr(tmp_path)
        ok, err = mgr.load(plugin_dir)
        assert ok is False
        assert "not signed" in err.lower()

    def test_load_missing_manifest(self, tmp_path: Path) -> None:
        mgr = self._make_mgr(tmp_path)
        ok, err = mgr.load(tmp_path)
        assert ok is False
        assert "manifest" in err.lower()

    def test_load_missing_entry_point(self, tmp_path: Path) -> None:
        key_dir = tmp_path / "keys"
        key_dir.mkdir(parents=True)
        plugin_dir = tmp_path / "plugins" / "bad-plugin"
        self._make_signed_plugin(plugin_dir, key_dir, trusted_key_dir_override=tmp_path / ".agentheim" / "trusted-keys")
        (plugin_dir / "plugin.py").unlink()
        mgr = self._make_mgr(tmp_path)
        ok, err = mgr.load(plugin_dir)
        assert ok is False
        assert any(term in err.lower() for term in ["entry point", "signature"])

    def test_load_rejects_tampered_plugin(self, tmp_path: Path) -> None:
        key_dir = tmp_path / "keys"
        key_dir.mkdir(parents=True)
        plugin_dir = tmp_path / "plugins" / "my-plugin"
        self._make_signed_plugin(plugin_dir, key_dir, trusted_key_dir_override=tmp_path / ".agentheim" / "trusted-keys")
        (plugin_dir / "plugin.py").write_text("x = 43\n", encoding="utf-8")
        mgr = self._make_mgr(tmp_path)
        ok, err = mgr.load(plugin_dir)
        assert ok is False
        assert "signature verification" in err.lower()

    def test_unload(self, tmp_path: Path) -> None:
        key_dir = tmp_path / "keys"
        key_dir.mkdir(parents=True)
        plugin_dir = tmp_path / "plugins" / "my-plugin"
        self._make_signed_plugin(plugin_dir, key_dir, trusted_key_dir_override=tmp_path / ".agentheim" / "trusted-keys")
        mgr = self._make_mgr(tmp_path)
        mgr.load(plugin_dir)
        assert "my-plugin" in mgr.list_loaded()
        mgr.unload("my-plugin")
        assert "my-plugin" not in mgr.list_loaded()


class TestSandbox:
    def test_sandbox_context(self) -> None:
        sandbox = Sandbox()
        with sandbox.run() as ctx:
            assert ctx.network_allowed is False

    def test_sandbox_call_success(self) -> None:
        sandbox = Sandbox()
        result = sandbox.call(lambda: 42)
        assert result == 42

    def test_sandbox_call_failure(self) -> None:
        sandbox = Sandbox()
        with pytest.raises(PluginSandboxError):
            sandbox.call(lambda: 1 / 0)
