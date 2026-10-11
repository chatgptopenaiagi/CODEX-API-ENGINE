"""PyInstaller entry point; the GUI remains an SDK consumer."""

import sys

from cae.gui import main

if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        # Package smoke test: creates the UI without loading credentials or networking.
        import tkinter as tk

        from cae.gui import Console

        root = tk.Tk()
        root.withdraw()
        console = Console(root)
        root.update()
        ok = bool(console.key.cget("show")) and len(console.buttons) == 5
        root.destroy()
        raise SystemExit(0 if ok else 1)
    else:
        main()
