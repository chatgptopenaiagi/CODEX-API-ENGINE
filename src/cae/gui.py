"""CAE Test Console: tkinter/ttk native themed UI, network work off the UI thread."""

import json
import queue
import threading
import tkinter as tk
from collections.abc import Callable
from functools import partial
from tkinter import messagebox, ttk
from typing import Any

from . import CAE
from .credential import CredentialManager
from .errors import CAEError


class Console:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("CAE Test Console · 0.2.0")
        root.geometry("820x600")
        root.minsize(640, 480)
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("TButton", padding=8)
        frame = ttk.Frame(root, padding=24)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="CODEX API ENGINE", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(
            frame, text="Protected credentials · Connection diagnostics", font=("Segoe UI", 11)
        ).pack(anchor="w", pady=(4, 20))
        ttk.Label(frame, text="Application profile").pack(anchor="w")
        self.profile = ttk.Entry(frame)
        self.profile.insert(0, "default")
        self.profile.pack(fill="x", pady=(4, 10))
        ttk.Label(frame, text="OpenAI API key").pack(anchor="w")
        self.key = ttk.Entry(frame, show="●")
        self.key.pack(fill="x", pady=(4, 12))
        self.buttons: list[ttk.Button] = []
        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(0, 12))
        for label, operation in (
            ("Add", "add"),
            ("Replace", "replace"),
            ("Remove", "remove"),
            ("Verify storage", "status"),
            ("Test connection", "test"),
        ):
            button = ttk.Button(actions, text=label, command=partial(self.run, operation))
            button.pack(side="left", padx=(0, 6))
            self.buttons.append(button)
        self.activity = tk.Text(
            frame, wrap="word", state="disabled", font=("Consolas", 10), height=14
        )
        self.activity.pack(fill="both", expand=True)
        ttk.Label(frame, text="API authentication is independent of Codex CLI login.").pack(
            anchor="w", pady=(12, 0)
        )
        self.results: queue.Queue[str] = queue.Queue()
        self.busy = False
        root.report_callback_exception = self._callback_error
        root.after(100, self.poll)

    def _callback_error(self, *args: Any) -> None:
        self.results.put('{"error": "ui_operation_failed"}')

    def run(self, operation: str) -> None:
        if self.busy:
            return
        if operation == "remove" and not messagebox.askyesno(
            "Remove credential", "Remove the selected profile's stored credential?"
        ):
            return
        profile = self.profile.get()
        secret = self.key.get() if operation in {"add", "replace"} else ""
        self.key.delete(0, "end")
        self.busy = True
        for button in self.buttons:
            button.configure(state="disabled")

        def work() -> None:
            nonlocal secret
            try:
                if operation in {"add", "replace", "remove"}:
                    manager = CredentialManager()
                    if operation == "remove":
                        manager.remove(profile)
                    else:
                        action: Callable[..., None] = getattr(manager, operation)
                        action(secret, profile)
                    result: dict[str, Any] = {"result": "success"}
                else:
                    engine = CAE(profile)
                    result = (
                        engine.test_connection() if operation == "test" else engine.get_status()
                    )
                output = json.dumps(result, indent=2)
            except CAEError as exc:
                output = json.dumps({"error": exc.code})
            except Exception:
                output = '{"error": "operation_failed"}'
            finally:
                secret = ""
            self.results.put(output)

        threading.Thread(target=work, daemon=True).start()

    def poll(self) -> None:
        try:
            while True:
                output = self.results.get_nowait()
                self.activity.configure(state="normal")
                self.activity.insert("end", output + "\n\n")
                # Keep bounded activity history; only fixed metadata is inserted.
                if int(self.activity.index("end-1c").split(".")[0]) > 500:
                    self.activity.delete("1.0", "100.0")
                self.activity.see("end")
                self.activity.configure(state="disabled")
                self.busy = False
                for button in self.buttons:
                    button.configure(state="normal")
        except queue.Empty:
            pass
        self.root.after(100, self.poll)


def main() -> None:
    root = tk.Tk()
    Console(root)
    root.mainloop()


if __name__ == "__main__":
    main()
