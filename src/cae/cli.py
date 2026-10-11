"""Human-operated console. Secrets enter only through a hidden prompt or import file."""

import argparse
import getpass
import json
import warnings
from collections.abc import Sequence
from pathlib import Path

from . import CAE, __version__
from .credential import CredentialManager
from .errors import CAEError


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cae", description="CAE credential and connection console"
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--profile", default="default")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("status", "test", "models", "add", "replace", "remove", "gui"):
        sub.add_parser(command)
    imp = sub.add_parser("import", help="Import without deleting the source file")
    imp.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "gui":
            from .gui import main as gui_main

            gui_main()
            return 0
        if args.command in {"add", "replace", "remove", "import"}:
            manager = CredentialManager()
            if args.command in {"add", "replace"}:
                # Refuse getpass's insecure echo fallback when no terminal is present.
                with warnings.catch_warnings():
                    warnings.simplefilter("error", getpass.GetPassWarning)
                    secret = getpass.getpass("OpenAI API key (hidden): ")
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
        engine = CAE(args.profile)
        result = {
            "status": engine.get_status,
            "test": engine.test_connection,
            "models": engine.list_models,
        }[args.command]()
        print(json.dumps(result, indent=2))
        if args.command == "test" and isinstance(result, dict):
            return 0 if result["authentication"] == "valid" else 1
        return 0
    except CAEError as exc:
        print(json.dumps({"error": exc.code}))
    except Exception:
        print(json.dumps({"error": "operation_failed"}))
    return 1
