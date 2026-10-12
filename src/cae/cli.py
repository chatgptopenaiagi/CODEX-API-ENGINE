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
    apps = sub.add_parser("apps", help="Operator-only application enrollment and policy")
    apps.add_argument("action", choices=("list", "register", "inspect", "authorize", "revoke"))
    apps.add_argument("--broker-config", type=Path, required=True)
    apps.add_argument("--id", dest="application")
    apps.add_argument("--image", type=Path)
    apps.add_argument("--operations", nargs="+", default=[])
    apps.add_argument("--models", nargs="+", default=[])
    apps.add_argument("--provider", dest="application_provider", default="openai")
    apps.add_argument("--profile", dest="application_profile", default="default")
    apps.add_argument("--max-requests-per-day", type=int, default=1000)
    apps.add_argument("--max-requests-per-minute", type=int)
    apps.add_argument("--max-concurrent-requests", type=int)
    apps.add_argument("--deny", action="store_true")
    args = parser.parse_args(argv)
    admin_runtime: AccessRuntime | None = None
    engine: CAE | None = None
    try:
        if args.command == "apps":
            from .registry import ApplicationRegistry

            registry = ApplicationRegistry(args.broker_config)
            if args.action == "list":
                app_result: object = registry.list()
            elif args.application is None:
                raise ConfigurationError()
            elif args.action == "register":
                if args.image is None:
                    raise ConfigurationError()
                app_result = registry.register(args.application, args.image)
            elif args.action == "inspect":
                app_result = registry.inspect(args.application)
            elif args.action == "revoke":
                app_result = registry.revoke(args.application)
            else:
                app_result = registry.authorize(args.application, args.application_provider,
                    args.application_profile, frozenset(args.operations),
                    models=frozenset(args.models), maximum=args.max_requests_per_day, deny=args.deny,
                    per_minute=args.max_requests_per_minute, concurrent=args.max_concurrent_requests)
            print(json.dumps(app_result, indent=2))
            return 0
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
