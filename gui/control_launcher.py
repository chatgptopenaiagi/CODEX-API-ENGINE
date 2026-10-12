import sys
import tkinter as tk

from cae.control_center import ControlCenter, main

if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        root = tk.Tk()
        root.withdraw()
        center = ControlCenter(root)
        root.update()
        ok = bool(center.key.cget("show")) and len(center.notebook.tabs()) == 8
        center.close()
        raise SystemExit(0 if ok else 1)
    else:
        main()
