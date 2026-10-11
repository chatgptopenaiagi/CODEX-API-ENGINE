"""Application B: independent desktop consumer; no credential/admin implementation."""

import argparse
import json
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from cae import BrokerClient, CAEError


class DesktopClient:
    def __init__(self, root, client, report=None, stop_file=None, verify_denial=False):
        self.root, self.client, self.report = root, client, report
        self.stop_file = stop_file
        self.verify_denial = verify_denial
        self.results = queue.Queue()
        self.stop = threading.Event()
        self.count = 0
        self.label = ttk.Label(root, text="Connecting to CAE broker…", padding=24)
        self.label.pack()
        root.title("CAE External Desktop Client")
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.worker = threading.Thread(target=self.poll, daemon=True)
        self.worker.start()
        self.timer = root.after(100, self.render)

    def poll(self):
        while not self.stop.is_set():
            try:
                status = self.client.get_status()
                diagnostics = self.client.diagnostics()
                denied = None
                if self.verify_denial:
                    try:
                        self.client.stop()
                    except CAEError as exc:
                        denied = exc.code == "access_denied"
                    else:
                        raise RuntimeError("Unexpected administrative enrollment")
                self.results.put({"broker_pid": status["broker_pid"],
                                  "authenticated_app": status["app"],
                                  "credential": diagnostics["credential"],
                                  "admin_denied": denied})
            except Exception:
                self.results.put({"error": "broker_unavailable"})
            self.stop.wait(0.5)

    def render(self):
        if self.stop_file and self.stop_file.exists():
            self.close()
            return
        while not self.results.empty():
            result = self.results.get_nowait()
            self.count += 1
            result.update(application="desktop", cycles=self.count, client_pid=os.getpid())
            self.label.configure(text=json.dumps(result, indent=2))
            if self.report:
                self.report.write_text(json.dumps(result), encoding="utf-8")
        self.timer = self.root.after(100, self.render)

    def close(self):
        self.stop.set()
        self.root.after_cancel(self.timer)
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--connection", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--stop-file", type=Path)
    parser.add_argument("--verify-denial", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    root = tk.Tk()
    if args.self_test:
        root.withdraw()
        ttk.Label(root, text="Installed public SDK desktop client").pack()
        root.update()
        root.destroy()
        return 0
    if args.connection is None:
        root.destroy()
        return 1
    try:
        client = BrokerClient(**json.loads(args.connection.read_text()))
        DesktopClient(root, client, args.report, args.stop_file, args.verify_denial)
        root.mainloop()
        return 0
    except Exception:
        root.destroy()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
