import json
import time
from unittest.mock import patch

import pytest


def test_control_center_offline_and_masked(tmp_path):
    import tkinter as tk

    from conftest import FAKE_KEY

    from cae.control_center import ControlCenter

    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Display unavailable")
    root.withdraw()
    center = ControlCenter(root)

    def drain():
        for _ in range(100):
            root.update()
            if not center.busy:
                break
            time.sleep(0.01)

    try:
        assert len(center.notebook.tabs()) == 8
        assert center.key.cget("show")
        center.submit(center.engine.providers)
        drain()
        assert "openai" in center.output.get("1.0", "end")
        center.key.insert(0, FAKE_KEY)
        with patch("cae.control_center.CredentialManager") as cls:
            center.credential_action("add")
            drain()
            cls.return_value.add.assert_called_once_with(FAKE_KEY, "default")
        assert center.key.get() == ""
        assert FAKE_KEY not in center.output.get("1.0", "end")
        from pathlib import Path

        cfg = tmp_path / "access.toml"
        cfg.write_text(Path("examples/access.toml").read_text())
        with patch("cae.control_center.filedialog.askopenfilename", return_value=str(cfg)):
            center.load_configuration()
        assert center.config_path == cfg
        center.apply_configuration()
        assert json.loads(center.results.get_nowait())
    finally:
        center.close()
        import gc

        center = None
        root = None
        gc.collect()


def test_operator_gui_selection_and_confirmed_admin(tmp_path):
    import tkinter as tk

    from test_application_registry import image
    from test_broker_lifecycle import configuration

    from cae.control_center import ControlCenter

    config, _, _ = configuration(tmp_path)
    selection = tmp_path / "selected.json"
    root = tk.Tk()
    root.withdraw()
    center = ControlCenter(root, selection_file=selection)

    def drain():
        for _ in range(600):
            root.update()
            if not center.busy:
                return
            time.sleep(0.01)
        assert not center.busy

    try:
        assert "Welcome" in center.broker_message.get()
        center.operator_action("status")
        assert "Choose" in center.broker_message.get()
        center.remember_broker()
        with patch("cae.control_center.filedialog.askopenfilename", return_value=""):
            center.choose_broker()
        with patch("cae.control_center.filedialog.askopenfilename", return_value=str(config)), patch("cae.control_center.messagebox.askyesno", return_value=False):
            center.choose_broker()
        assert center.operator is None
        with patch("cae.control_center.filedialog.askopenfilename", return_value=str(config)), patch("cae.control_center.messagebox.askyesno", return_value=True):
            center.choose_broker()
            center.remember_broker()
        assert selection.exists()
        with patch("cae.control_center.messagebox.askyesno", return_value=True):
            center.remember_broker()
        assert "Nothing was overwritten" in center.broker_message.get()
        center.operator_action("applications")
        drain()
        assert "test-admin" in center.output.get("1.0", "end")
        center.application_id.insert(0, "sample")
        executable = image(tmp_path)
        with patch("cae.control_center.filedialog.askopenfilename", return_value=str(executable)), patch("cae.control_center.messagebox.askyesno", return_value=True):
            center.register_application()
            drain()
            center.revoke_application()
            drain()
        assert '"revoked": true' in center.output.get("1.0", "end")
        center.operator_action("status")  # No broker started: actionable bounded failure.
        drain()
        assert "guidance" in center.output.get("1.0", "end")
        with patch("cae.control_center.filedialog.askopenfilename", return_value=str(tmp_path / "missing.json")):
            center.choose_broker()
        assert "invalid" in center.broker_message.get()
    finally:
        center.close()
    root = tk.Tk()
    root.withdraw()
    center = ControlCenter(root, selection_file=selection)
    assert "verified offline" in center.broker_message.get()
    center.close()
    selection.write_text("{}")
    root = tk.Tk()
    root.withdraw()
    center = ControlCenter(root, selection_file=selection)
    assert "No connection was attempted" in center.broker_message.get()
    center.close()
