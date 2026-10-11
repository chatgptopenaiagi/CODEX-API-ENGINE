import time
from unittest.mock import patch

import pytest


def test_gui_mask_clear_and_worker():
    import tkinter as tk

    from conftest import FAKE_KEY

    from cae.gui import Console

    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Display not available")
    root.withdraw()
    try:
        console = Console(root)
        assert console.key.cget("show")
        console.key.insert(0, FAKE_KEY)
        with patch("cae.gui.CredentialManager") as manager:
            console.run("add")
            for _ in range(100):
                root.update()
                if not console.busy:
                    break
                time.sleep(0.01)
            manager.return_value.add.assert_called_once_with(FAKE_KEY, "default")
        assert console.key.get() == ""
        assert not console.busy
        assert FAKE_KEY not in console.activity.get("1.0", "end")
        with patch("cae.gui.CAE") as engine:
            engine.return_value.test_connection.return_value = {"authentication": "valid"}
            console.run("test")
            for _ in range(100):
                root.update()
                if not console.busy:
                    break
                time.sleep(0.01)
        assert "valid" in console.activity.get("1.0", "end")
    finally:
        root.destroy()
        import gc

        console = None
        root = None
        gc.collect()
