"""Application A: independent console consumer using only the installed public SDK."""

import argparse
import json
import os
import time
from pathlib import Path

from cae import BrokerClient, CAEError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--connection", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--stop-file", type=Path)
    parser.add_argument("--verify-denial", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--route-request", type=Path,
                        help="One bounded capability request JSON; no automatic replay")
    args = parser.parse_args()
    if args.self_test:
        return 0
    if args.connection is None:
        return 1
    connection = json.loads(args.connection.read_text())
    client = BrokerClient(**connection)
    if args.route_request:
        try:
            if args.route_request.stat().st_size > 65536:
                return 1
            request = json.loads(args.route_request.read_text(encoding="utf-8"))
            status = client.get_status()
            result = {"status": status, "response": client.request("route", **request)}
            if args.report:
                args.report.write_text(json.dumps(result), encoding="utf-8")
            else:
                print(json.dumps(result), flush=True)
            return 0
        except CAEError as exc:
            if args.report:
                args.report.write_text(json.dumps({"error": exc.code}), encoding="utf-8")
            return 2
        except Exception:
            return 1
    count = 0
    try:
        while True:
            if args.stop_file and args.stop_file.exists():
                return 0
            status = client.get_status()
            diagnostics = client.diagnostics()
            denied = None
            if args.verify_denial:
                try:
                    client.stop()
                except CAEError as exc:
                    denied = exc.code == "access_denied"
                else:
                    return 1
            count += 1
            result = {"application": "console", "cycles": count,
                      "client_pid": os.getpid(),
                      "broker_pid": status["broker_pid"], "authenticated_app": status["app"],
                      "credential": diagnostics["credential"], "admin_denied": denied}
            if args.report:
                args.report.write_text(json.dumps(result), encoding="utf-8")
            else:
                print(json.dumps(result), flush=True)
            time.sleep(0.5)
    except KeyboardInterrupt:
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
