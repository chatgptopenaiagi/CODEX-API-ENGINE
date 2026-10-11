"""Report sharing is a lab filesystem concern, not a broker reconnect failure."""
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from cae.errors import CAEError


def test_report_writer_recovers_after_windows_reader_closes(tmp_path, monkeypatch):
    class Client:
        def connect(self):
            return {"broker_pid": 123}

        def health(self, *args):
            return {}

        def models(self, *args):
            return {"models": ["test"]}

        def capabilities(self):
            return {}

        def request(self, *args, **kwargs):
            raise CAEError()

    monkeypatch.setitem(sys.modules, "cae_client", SimpleNamespace(CAEClient=Client, CAEError=CAEError))
    spec = importlib.util.spec_from_file_location("python_lab", "integration-lab/python-client/main.py")
    assert spec and spec.loader
    lab = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lab)
    report = tmp_path / "report.json"
    report.write_text("original")
    reader = report.open("rb")
    iterations = []

    def step(_):
        iterations.append(1)
        if len(iterations) == 1:
            assert report.read_text() == "original"
            reader.close()
        else:
            Path(str(report) + ".stop").touch()

    monkeypatch.setattr(sys, "argv", ["main.py", str(report)])
    monkeypatch.setattr(lab.time, "sleep", step)
    try:
        lab.main()
    finally:
        reader.close()
    assert len(iterations) == 2
    assert json.loads(report.read_text())["status"]["broker_pid"] == 123


def test_original_windows_reader_blocks_atomic_report_replacement(tmp_path):
    report = tmp_path / "report.json"
    replacement = tmp_path / "report.new"
    report.write_bytes(b'"old"')
    replacement.write_bytes(b'"new"')
    with Path.open(report, "rb"), pytest.raises(PermissionError):
        replacement.replace(report)
    replacement.replace(report)
    assert report.read_bytes() == b'"new"'


def test_restart_acceptance_waits_for_new_broker_not_only_new_file(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("client_validation", "scripts/validate_clients.py")
    assert spec and spec.loader
    lab = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lab)
    report = tmp_path / "report.json"
    value = {"status":{"app":"sample","broker_mode":"named_pipe","broker_pid":123},
             "models":["lab-model"],"denied":True,"malformed":True,"restricted":True}
    report.write_text(json.dumps(value))
    iterations = []

    def step(_):
        iterations.append(1)
        value["status"]["broker_pid"] = 456
        report.write_text(json.dumps(value))

    monkeypatch.setattr(lab.time,"sleep",step)
    result = lab.wait_reports({"sample":report},previous_pid=123)
    assert len(iterations) == 1
    assert result["sample"]["status"]["broker_pid"] == 456
