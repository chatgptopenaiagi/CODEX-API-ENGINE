"""Human-operated console. Secrets enter only through a hidden prompt or import file."""

import argparse
import getpass
import json
import warnings
from collections.abc import Sequence
from pathlib import Path

from . import CAE, __version__
from .access import AccessRuntime
from .config import load_runtime, parse_config
from .credential import CredentialManager
from .errors import CAEError, ConfigurationError


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cae", description="CAE credential and connection console"
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--profile", default="default")
    parser.add_argument("--app", default="cae-console")
    parser.add_argument("--provider", default="openai")
    parser.add_argument("--config", type=Path, help="Explicit administrator-owned TOML policy")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in (
        "status",
        "test",
        "models",
        "add",
        "replace",
        "remove",
        "gui",
        "health",
        "providers",
        "diagnostics",
        "connect",
        "broker",
        "audit",
        "policies",
    ):
        command_parser = sub.add_parser(command)
        if command == "broker":
            command_parser.add_argument("action", nargs="?", choices=(
                "start", "stop", "restart", "status", "health", "diagnostics"))
            command_parser.add_argument("--config", dest="broker_config", type=Path)
    imp = sub.add_parser("import", help="Import without deleting the source file")
    imp.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    admin_runtime: AccessRuntime | None = None
    engine: CAE | None = None
    try:
        if args.command == "broker" and args.action is not None:
            from .broker_control import control

            if args.broker_config is None:
                raise ConfigurationError()
            print(json.dumps(control(args.action, args.broker_config), indent=2))
            return 0
        if args.command == "gui":
            from .control_center import main as gui_main

            gui_main()
            return 0
        if args.command in {"add", "replace", "remove", "import"}:
            if args.config is not None:
                specs, _ = parse_config(args.config.read_text(encoding="utf-8"))
                selected = next((spec for spec in specs if spec.name == args.provider), None)
                if selected is None or not selected.authenticated:
                    raise ConfigurationError()
                admin_runtime = load_runtime(args.config)
                manager = CredentialManager(provider=selected.kind, audit=admin_runtime.audit_log)
            else:
                manager = (
                    CredentialManager()
                    if args.provider == "openai"
                    else CredentialManager(provider=args.provider)
                )
            if args.command in {"add", "replace"}:
                # Refuse getpass's insecure echo fallback when no terminal is present.
                with warnings.catch_warnings():
                    warnings.simplefilter("error", getpass.GetPassWarning)
                    secret = getpass.getpass("Provider API key (hidden): ")
                try:
                    getattr(manager, args.command)(secret, args.profile)
                finally:
                    secret = ""
            elif args.command == "remove":
                manager.remove(args.profile)
            else:
                manager.import_file(args.path, args.profile)
            print(json.dumps({"result": "success"}))
            return 0
        engine = (
            CAE(args.profile)
            if args.config is None and args.app == "cae-console" and args.provider == "openai"
            else CAE(args.profile, app=args.app, config=args.config, provider=args.provider)
        )
        result = {
            "status": engine.get_status,
            "test": engine.test_connection,
            "models": engine.list_models,
            "health": engine.health,
            "providers": engine.providers,
            "diagnostics": engine.diagnostics,
            "connect": engine.connect,
            "broker": engine.diagnostics,
            "audit": engine.audit,
            "policies": engine.policies,
        }[args.command]()
        print(json.dumps(result, indent=2))
        if args.command in {"test", "connect"} and isinstance(result, dict):
            return (
                0
                if result["authentication"] in {"valid", "not_required"} and not result.get("error")
                else 1
            )
        return 0
    except CAEError as exc:
        print(json.dumps({"error": exc.code}))
    except Exception:
        print(json.dumps({"error": "operation_failed"}))
    finally:
        if admin_runtime is not None:
            admin_runtime.close()
        if engine is not None:
            engine.close()
    return 1
