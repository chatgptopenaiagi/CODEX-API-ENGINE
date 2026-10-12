"""Human administration UI. Configuration/credentials never belong to application sessions."""

import json
import queue
import sys
import threading
import tkinter as tk
from collections.abc import Callable
from functools import partial
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from .access import AccessRuntime
from .config import load_runtime, parse_config
from .credential import CredentialManager
from .engine import CAE
from .errors import CAEError
from .operator_view import OperatorView
from .version import __version__


class ControlCenter:
    def __init__(self, root: tk.Tk, *, selection_file: Path | None = None) -> None:
        self.root = root
        self.runtime = AccessRuntime.default()
        self.engine = CAE(runtime=self.runtime)
        self.config_path: Path | None = None
        self.busy = False
        self._worker: threading.Thread | None = None
        self.results: queue.Queue[str] = queue.Queue()
        self.buttons: list[ttk.Button] = []
        self.operator: OperatorView | None = None
        self.selection_file = selection_file or (
            Path(sys.executable).parent / "cae-control-selection.json"
            if getattr(sys, "frozen", False) else None
        )
        root.title("CAE Control Center · " + __version__)
        root.geometry("1040x760")
        root.minsize(860, 680)
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("TButton", padding=6)
        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="CODEX ACCESS ENGINE", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Capabilities, protected credentials and human oversight").pack(
            anchor="w", pady=(4, 12)
        )
        self.notebook = ttk.Notebook(frame)
        self.notebook.pack(fill="both", expand=True)
        pages = {}
        for name in ("Broker", "Applications", "Overview", "Providers", "Credentials", "Audit", "Policies", "Help"):
            page = ttk.Frame(self.notebook, padding=16)
            self.notebook.add(page, text=name)
            pages[name] = page
        self.broker_message = tk.StringVar(value="Welcome. Select an existing broker configuration to begin. No broker is started automatically.")
        ttk.Label(pages["Broker"], textvariable=self.broker_message, wraplength=760).pack(anchor="w", pady=8)
        self._button(pages["Broker"], "Choose broker configuration…", self.choose_broker)
        self._button(pages["Broker"], "Check verified broker status", lambda: self.operator_action("status"))
        self._button(pages["Broker"], "Remember selection for next launch", self.remember_broker)
        ttk.Label(pages["Applications"], text="Operator enrollment is required. Registration grants no provider access.\nRevocation affects new connections; accepted work may finish.", wraplength=760).pack(anchor="w", pady=8)
        self._button(pages["Applications"], "List applications and policy limits", lambda: self.operator_action("applications"))
        ttk.Label(pages["Applications"], text="Application identifier (lowercase letters, digits, hyphen or underscore)").pack(anchor="w")
        self.application_id = ttk.Entry(pages["Applications"])
        self.application_id.pack(fill="x", pady=8)
        self._button(pages["Applications"], "Register executable…", self.register_application)
        self._button(pages["Applications"], "Revoke application…", self.revoke_application)
        ttk.Label(pages["Help"], text=(
            "1. Choose an operator-provided broker.json; review its executable identity.\n"
            "2. Check status. Missing broker: ask its operator to start it.\n"
            "3. Access denied: the exact Control Center image must already be enrolled.\n"
            "4. Applications lists existing grants, routing modes and quota limits.\n"
            "Authorization/provider editing still uses the documented administration CLI.\n"
            "Overview, Providers, Credentials, Audit and Policies retain the separate\n"
            "trusted in-process interface; they do not administer the selected broker.\n"
            "No automatic cloud calls, telemetry, enrollment or credential changes.\n"
            "Closing this window leaves the independent broker running.\n"
            "Read docs/QUICKSTART_WINDOWS.md in the source distribution."
        ), wraplength=760, justify="left").pack(anchor="w", pady=8)
        self._button(
            pages["Overview"], "Health snapshot (offline)", lambda: self.submit(self.engine.health)
        )
        self._button(
            pages["Overview"], "Diagnostics (offline)", lambda: self.submit(self.engine.diagnostics)
        )
        self._button(pages["Overview"], "Test connection", lambda: self.submit(self.engine.connect))
        ttk.Label(
            pages["Overview"],
            text="The broker is in-process. It does not isolate hostile programs under the same Windows account.",
            wraplength=800,
        ).pack(anchor="w", pady=16)
        self._button(
            pages["Providers"], "Inspect providers", lambda: self.submit(self.engine.providers)
        )
        self.active_provider = ttk.Combobox(
            pages["Providers"], values=("openai",), state="readonly"
        )
        self.active_provider.set("openai")
        self.active_provider.pack(fill="x", pady=8)
        self.active_provider.bind("<<ComboboxSelected>>", self.select_provider)
        self._button(pages["Providers"], "List models", lambda: self.submit(self.engine.models))
        ttk.Label(
            pages["Providers"],
            text="Select provider/profile by editing the validated policy configuration.\nUse the CLI --provider option to probe other configured providers.",
        ).pack(anchor="w", pady=12)
        credentials = pages["Credentials"]
        ttk.Label(credentials, text="Provider kind / credential namespace").pack(anchor="w")
        self.provider = ttk.Combobox(
            credentials,
            values=("openai", "azure-openai", "anthropic", "gemini", "vllm", "lmstudio", "custom"),
            state="readonly",
        )
        self.provider.set("openai")
        self.provider.pack(fill="x", pady=4)
        ttk.Label(credentials, text="Profile").pack(anchor="w")
        self.profile = ttk.Entry(credentials)
        self.profile.insert(0, "default")
        self.profile.pack(fill="x", pady=4)
        self.key = ttk.Entry(credentials, show="●")
        self.key.pack(fill="x", pady=4)
        for label, action in (
            ("Add", "add"),
            ("Replace / local rotation", "replace"),
            ("Remove local credential", "remove"),
        ):
            self._button(credentials, label, partial(self.credential_action, action))
        ttk.Label(
            credentials, text="Removal does not revoke the provider's key. No export is available."
        ).pack(anchor="w", pady=10)
        self._button(
            pages["Audit"],
            "Read administrative audit",
            lambda: self.submit(self.runtime.audit_log.events),
        )
        ttk.Label(
            pages["Audit"], text="Metadata only. No prompts, responses, keys or exception bodies."
        ).pack(anchor="w", pady=12)
        policies = pages["Policies"]
        controls = ttk.Frame(policies)
        controls.pack(fill="x")
        self._button(controls, "Load configuration", self.load_configuration)
        self._button(controls, "Validate and apply", self.apply_configuration)
        self.editor = tk.Text(policies, height=12, wrap="none", font=("Consolas", 10))
        self.editor.pack(fill="both", expand=True, pady=8)
        ttk.Label(
            policies,
            text="Explicit allow/deny rules. Provider export/modification is never an application capability.",
        ).pack(anchor="w")
        self.output = tk.Text(
            frame, height=12, state="disabled", wrap="word", font=("Consolas", 10)
        )
        self.output.pack(fill="both", expand=True, pady=(12, 0))
        root.report_callback_exception = self.callback_error
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._poll_id = root.after(100, self.poll)
        if self.selection_file is not None and self.selection_file.exists():
            try:
                self.operator = OperatorView.restore(self.selection_file)
                self.broker_message.set("Saved identity verified offline. Click Check verified broker status to connect.")
            except Exception:
                self.broker_message.set("Saved selection is invalid or the executable changed. Choose and review configuration again. No connection was attempted.")

    def choose_broker(self) -> None:
        selected = filedialog.askopenfilename(filetypes=[("Broker configuration", "*.json")])
        if not selected:
            return
        try:
            candidate = OperatorView(Path(selected))
            server = candidate.settings.server
            if not messagebox.askyesno("Trust this broker configuration?",
                    f"Only select configuration supplied by your operator.\nExecutable: {server.image}\nSHA-256: {server.sha256}\nThis does not grant this GUI administrative access."):
                return
            self.operator = candidate
            self.broker_message.set("Identity selected. Check status to connect; no broker was started or changed.")
        except Exception:
            self.broker_message.set("Configuration is invalid or executable identity does not match. Ask the operator for a current configuration.")

    def operator_action(self, name: str) -> None:
        if self.operator is None:
            self.broker_message.set("Choose a broker configuration first. Do not disable identity verification.")
            return
        action = self.operator.status if name == "status" else self.operator.applications
        self.submit(action)

    def remember_broker(self) -> None:
        if self.operator is None or self.selection_file is None:
            self.broker_message.set("Select a broker first. Remembered portable selection is available in the packaged application.")
            return
        if messagebox.askyesno("Remember this selection?", "Create a non-secret selection beside this portable executable? Existing files are never overwritten."):
            try:
                self.operator.remember(self.selection_file)
                self.broker_message.set("Selection saved. Keep the portable directory private to your Windows account.")
            except Exception:
                self.broker_message.set("Selection could not be saved: folder may be read-only or a selection already exists. Nothing was overwritten.")

    def register_application(self) -> None:
        if self.operator is None or self.busy:
            self.operator_action("applications")
            return
        selected = filedialog.askopenfilename(filetypes=[("Windows executable", "*.exe")])
        app = self.application_id.get()
        if selected and messagebox.askyesno("Register application?", "Register this exact executable without provider permissions? Only register code you trust."):
            operator = self.operator
            self.submit(lambda: operator.register(app, Path(selected)))

    def revoke_application(self) -> None:
        if self.operator is None or self.busy:
            self.operator_action("applications")
            return
        app = self.application_id.get()
        if messagebox.askyesno("Revoke application?", "Revoke the specified application? Accepted work is not cancelled. The result reports whether restart is required."):
            operator = self.operator
            self.submit(lambda: operator.revoke(app))

    def _button(self, parent: ttk.Frame, label: str, action: Callable[[], None]) -> None:
        button = ttk.Button(parent, text=label, command=action)
        button.pack(anchor="w", pady=3)
        self.buttons.append(button)

    def callback_error(self, *args: Any) -> None:
        self.results.put('{"error":"ui_operation_failed"}')

    def select_provider(self, event: Any = None) -> None:
        if not self.busy:
            self.engine = CAE(runtime=self.runtime, provider=self.active_provider.get())

    def refresh_providers(self) -> None:
        names = [item["name"] for item in self.runtime.providers("cae-console", "default")]
        self.active_provider.configure(values=names)
        self.active_provider.set(names[0] if names else "openai")
        self.select_provider()

    def submit(self, action: Callable[[], Any]) -> None:
        if self.busy:
            return
        self.busy = True
        self.active_provider.configure(state="disabled")
        for button in self.buttons:
            button.configure(state="disabled")

        def worker() -> None:
            try:
                output = json.dumps(action(), indent=2)
            except CAEError as exc:
                guidance = {
                    "access_denied": "This executable is not authorized. Ask the operator to enroll the exact image; do not bypass verification.",
                    "broker_unavailable": "Broker unavailable or identity mismatch. Ask the operator to verify the selected installation.",
                    "invalid_configuration": "Configuration or executable identity is invalid. Review with the operator.",
                    "audit_unavailable": "Audit storage is unavailable. Protected operations remain denied.",
                }
                output = json.dumps({"error": exc.code, "guidance": guidance.get(exc.code, "Operation failed. Consult troubleshooting; no automatic retry was made.")})
            except Exception:
                output = '{"error":"operation_failed"}'
            self.results.put(output)

        self._worker = threading.Thread(target=worker, daemon=True)
        self._worker.start()

    def credential_action(self, operation: str) -> None:
        if self.busy:
            return
        if operation == "remove" and not messagebox.askyesno(
            "Remove local credential",
            "Remove this profile's stored credential? Provider revocation is separate.",
        ):
            return
        secret = self.key.get()
        self.key.delete(0, "end")
        provider, profile = self.provider.get(), self.profile.get()

        def action() -> dict[str, str]:
            nonlocal secret
            try:
                manager = CredentialManager(provider=provider, audit=self.runtime.audit_log)
                if operation == "remove":
                    manager.remove(profile)
                elif operation == "add":
                    manager.add(secret, profile)
                else:
                    manager.replace(secret, profile)
                return {"credential_operation": "success"}
            finally:
                secret = ""

        self.submit(action)

    def load_configuration(self) -> None:
        selected = filedialog.askopenfilename(filetypes=[("CAE configuration", "*.toml")])
        if not selected:
            return
        path = Path(selected)
        try:
            if path.stat().st_size > 128_000 or path.is_symlink():
                raise ValueError()
            text = path.read_text(encoding="utf-8")
            parse_config(text)
            runtime = load_runtime(path)
        except Exception:
            self.results.put('{"error":"invalid_configuration"}')
            return
        self.runtime.close()
        self.runtime, self.engine = runtime, CAE(runtime=runtime)
        self.config_path = path
        self.refresh_providers()
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", text)
        self.results.put('{"configuration":"loaded"}')

    def apply_configuration(self) -> None:
        text = self.editor.get("1.0", "end-1c")
        try:
            parse_config(text)
            if self.config_path is None:
                selected = filedialog.asksaveasfilename(
                    defaultextension=".toml", filetypes=[("CAE configuration", "*.toml")]
                )
                if not selected:
                    return
                path = Path(selected)
            else:
                path = self.config_path
            if path.name.lower() == "apy_key.txt" or path.suffix != ".toml" or path.is_symlink():
                raise ValueError()
            # Validated administration file only; never application-supplied credentials.
            path.write_text(text, encoding="utf-8")
            runtime = load_runtime(path)
        except Exception:
            self.results.put('{"error":"configuration_update_failed"}')
            return
        self.runtime.close()
        self.runtime, self.engine, self.config_path = runtime, CAE(runtime=runtime), path
        self.refresh_providers()
        self.results.put('{"configuration":"applied"}')

    def poll(self) -> None:
        try:
            while True:
                message = self.results.get_nowait()
                self.output.configure(state="normal")
                self.output.insert("end", message + "\n")
                if int(self.output.index("end-1c").split(".")[0]) > 500:
                    self.output.delete("1.0", "100.0")
                self.output.see("end")
                self.output.configure(state="disabled")
                self.busy = False
                self.active_provider.configure(state="readonly")
                for button in self.buttons:
                    button.configure(state="normal")
        except queue.Empty:
            pass
        self._poll_id = self.root.after(100, self.poll)

    def close(self) -> None:
        if not self.busy:
            if self._worker is not None:
                self._worker.join(timeout=0.2)
                if self._worker.is_alive():
                    return
            self.root.after_cancel(self._poll_id)
            self.runtime.close()
            self.root.destroy()


def main() -> None:
    root = tk.Tk()
    ControlCenter(root)
    root.mainloop()
