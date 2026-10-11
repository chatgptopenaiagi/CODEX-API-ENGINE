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
        assert len(center.notebook.tabs()) == 5
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
