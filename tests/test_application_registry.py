import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from test_broker_lifecycle import configuration, launch

from cae import BrokerClient, __version__
from cae.broker_control import control
from cae.cli import main as cli_main
from cae.config import parse_config
from cae.errors import AccessDenied, ConfigurationError
from cae.ipc_protocol import BrokerSettings
from cae.pipe_transport import IPCError, digest
from cae.registry import ApplicationRegistry, _atomic


def image(tmp_path: Path, name: str = "client") -> Path:
    path = tmp_path / (name + ".exe")
    path.write_bytes(b"synthetic-image-for-enrollment-only")
    return path


def test_registry_lifecycle_and_quota_identity(tmp_path):
    config, settings, _ = configuration(tmp_path)
    registry = ApplicationRegistry(config)
    assert registry.list()[0]["app"] == "test-admin"
    registry.register("sample", image(tmp_path))
    record = registry.inspect("sample")
    assert record["policies"] == [] and not record["admin"] and not record["revoked"]
    assert record["principal_sid"].startswith("S-1-") and record["registered_at"]
    assert registry.authorize("sample", "openai", "default", frozenset({"models"}),
                              maximum=10, per_minute=2, concurrent=1)["effective"] == "broker_restart"
    first = registry.inspect("sample")["policies"][0]
    registry.authorize("sample", "openai", "default", frozenset({"models"}), maximum=5)
    second = registry.inspect("sample")["policies"][0]
    assert first["id"] == second["id"] and second["max_requests_per_day"] == 5
    assert second["max_requests_per_minute"] == 2 and second["max_concurrent_requests"] == 1
    registry.authorize("sample", "openai", "default", frozenset({"chat"}), deny=True)
    assert len(registry.inspect("sample")["policies"]) == 2
    assert registry.revoke("sample")["effective"] == "broker_restart"
    assert ApplicationRegistry(config).inspect("sample")["revoked"]
    assert not any(row.app == "sample" for row in BrokerSettings.load(config).clients)
    # Revoked identifiers cannot reactivate old policy grants through registration.
    with pytest.raises(ConfigurationError):
        registry.register("sample", image(tmp_path, "another"))
    assert settings.runtime.is_file()


def test_administration_requires_authenticated_admin(tmp_path):
    config, _, _ = configuration(tmp_path)
    value = json.loads(config.read_text())
    value["clients"][0]["admin"] = False
    config.write_text(json.dumps(value))
    original = config.read_bytes()
    with pytest.raises(AccessDenied):
        ApplicationRegistry(config).register("sample", image(tmp_path))
    assert config.read_bytes() == original
    assert not config.with_name("broker.apps.lock").exists()


def test_invalid_changes_do_not_mutate_configuration(tmp_path):
    config, settings, _ = configuration(tmp_path)
    registry = ApplicationRegistry(config)
    registry.register("sample", image(tmp_path))
    before = config.read_bytes(), settings.runtime.read_bytes()
    with pytest.raises(ConfigurationError):
        registry.register("sample", image(tmp_path, "other"))
    with pytest.raises(ConfigurationError):
        registry.register("other", tmp_path / "client.exe")
    with pytest.raises(ConfigurationError):
        registry.register("other", tmp_path / "absent.exe")
    with pytest.raises(AccessDenied):
        registry.revoke("test-admin")
    with pytest.raises(AccessDenied):
        registry.revoke("missing")
    with pytest.raises(ConfigurationError):
        registry.inspect("missing")
    with pytest.raises(AccessDenied):
        registry.authorize("missing", "openai", "default", frozenset({"models"}))
    with pytest.raises(ConfigurationError):
        registry.authorize("sample", "missing", "default", frozenset({"models"}))
    with pytest.raises(ConfigurationError):
        registry.authorize("sample", "openai", "default", frozenset({"credentials.export"}))
    assert (config.read_bytes(), settings.runtime.read_bytes()) == before


def test_registry_concurrent_writers_and_bad_metadata(tmp_path):
    config, _, _ = configuration(tmp_path)
    registry = ApplicationRegistry(config)
    images = [image(tmp_path, "one"), image(tmp_path, "two")]
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda p: registry.register(p.stem, p), images))
    assert len(results) == 2
    assert {row["app"] for row in registry.list()} == {"one", "two", "test-admin"}
    registry.metadata.write_text('{"one":{"revoked":"invalid"}}')
    with pytest.raises(ConfigurationError):
        registry.list()


def test_cli_registry_commands(tmp_path, capsys):
    config, settings, _ = configuration(tmp_path)
    prefix = ["apps"]
    tail = ["--broker-config", str(config)]
    assert cli_main([*prefix, "list", *tail]) == 0
    assert cli_main([*prefix, "register", *tail, "--id", "sample", "--image", str(image(tmp_path))]) == 0
    assert cli_main([*prefix, "inspect", *tail, "--id", "sample"]) == 0
    assert cli_main([*prefix, "authorize", *tail, "--id", "sample", "--operations", "models"]) == 0
    _, rules = parse_config(settings.runtime.read_text())
    assert any(rule.app == "sample" for rule in rules)
    assert cli_main([*prefix, "revoke", *tail, "--id", "sample"]) == 0
    assert cli_main([*prefix, "register", *tail, "--id", "sample"]) == 1
    assert cli_main([*prefix, "inspect", *tail]) == 1
    assert "principal_sid" in capsys.readouterr().out


def test_atomic_failure_preserves_original(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text("original")
    class FailingLibrary:
        @property
        def ReplaceFileW(self):
            def replace(*args):
                return 0
            return replace
    monkeypatch.setattr("cae.registry.ctypes.WinDLL", lambda *args, **kwargs: FailingLibrary())
    with pytest.raises(ConfigurationError):
        _atomic(path, "replacement")
    assert path.read_text() == "original"
    assert not list(tmp_path.glob(".cae-edit-*"))


@pytest.mark.parametrize("restore_fails", [False, True])
def test_partial_replace_failure_retains_recoverable_original(tmp_path, monkeypatch, restore_fails):
    path = tmp_path / "config.json"
    path.write_text("original")
    original_replace = os.replace

    class PartialFailure:
        @property
        def ReplaceFileW(self):
            def replace(destination, source, backup, *args):
                original_replace(destination, backup)
                return 0
            return replace

    monkeypatch.setattr("cae.registry.ctypes.WinDLL", lambda *args, **kwargs: PartialFailure())
    if restore_fails:
        def fail(*args):
            raise OSError()
        monkeypatch.setattr("cae.registry.os.replace", fail)
    with pytest.raises(ConfigurationError):
        _atomic(path, "replacement")
    if restore_fails:
        backups = list(tmp_path.glob(".cae-edit-*.previous"))
        assert len(backups) == 1 and backups[0].read_text() == "original"
    else:
        assert path.read_text() == "original"
        assert not list(tmp_path.glob(".cae-edit-*"))


def test_registry_refuses_symlinks_and_oversize_metadata(tmp_path):
    config, _, _ = configuration(tmp_path)
    alias = tmp_path / "alias.json"
    alias.symlink_to(config)
    with pytest.raises(ConfigurationError):
        ApplicationRegistry(alias)
    with pytest.raises(ConfigurationError):
        _atomic(alias, "{}")
    registry = ApplicationRegistry(config)
    registry.metadata.write_bytes(b"x" * 65537)
    with pytest.raises(ConfigurationError):
        registry.list()
    lock = config.with_name("broker.apps.lock")
    lock.unlink()
    lock.symlink_to(config)
    with pytest.raises(ConfigurationError):
        registry.list()


def test_administrative_lock_timeout_is_bounded(tmp_path, monkeypatch):
    config, _, _ = configuration(tmp_path)
    import msvcrt

    def busy(*args):
        raise OSError()

    ticks = iter([0, 10])
    monkeypatch.setattr(msvcrt, "locking", busy)
    monkeypatch.setattr("cae.registry.time.monotonic", lambda: next(ticks))
    with pytest.raises(ConfigurationError):
        ApplicationRegistry(config).list()


@pytest.mark.parametrize("host", ["source", "frozen"])
def test_running_broker_reloads_revocation_without_restart(tmp_path, host):
    executable = Path(__file__).resolve().parents[1] / "dist/0.4.0-clients/CAE-Cpp-Client.exe"
    if not executable.exists():
        pytest.skip("Build clients first for the additional native revocation acceptance test")
    config, settings, client = configuration(tmp_path)
    registry = ApplicationRegistry(config)
    registry.register("native", executable)
    connection = tmp_path / "client.json"
    connection.write_text(json.dumps({"pipe": settings.pipe, "server_image": settings.server.image,
                                      "server_sha256": settings.server.sha256}))
    env = dict(os.environ, CAE_CONNECTION_FILE=str(connection))
    if host == "source":
        process, status = launch(config, client)
    else:
        binary = executable.parent.parent / __version__ / "CAE-Broker.exe"
        if not binary.exists():
            pytest.skip("Build the development broker before frozen acceptance")
        data = json.loads(config.read_text())
        data["server"].update(image=str(binary), sha256=digest(binary))
        config.write_text(json.dumps(data))
        descriptor = json.loads(connection.read_text())
        descriptor.update(server_image=str(binary), server_sha256=digest(binary))
        connection.write_text(json.dumps(descriptor))
        client = BrokerClient(**descriptor)
        status = control("start", config)
    try:
        first = subprocess.run([str(executable), "--probe"], env=env, capture_output=True, timeout=10)
        assert first.returncode == 0 and first.stdout.strip() == b"ok"
        assert registry.revoke("native")["effective"] == "next_connection"
        second = subprocess.run([str(executable), "--probe"], env=env, capture_output=True, timeout=10)
        assert second.returncode == 0 and second.stdout.strip() == b"access_denied"
        assert client.get_status()["broker_pid"] == status["broker_pid"]
    finally:
        if host == "source":
            client.stop()
            process.wait(timeout=10)
            assert process.returncode == 0
        else:
            assert control("stop", config) == {"broker": "stopped"}
            with pytest.raises(IPCError):
                client.get_status()
