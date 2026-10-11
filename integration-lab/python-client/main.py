"""Independent application importing only the installed public client package."""

import json
import os
import sys
import time
from pathlib import Path

from cae_client import CAEClient, CAEError


def main() -> None:
    if sys.argv[1] == "--probe":
        try:
            CAEClient(timeout=1).connect()
            print("ok")
        except CAEError as exc:
            print(exc.code)
        return
    client = CAEClient()
    output = Path(sys.argv[1])
    while not Path(str(output) + ".stop").exists():
        try:
            status = client.connect()
            client.health("lab")
            models, capabilities = client.models("lab"), client.capabilities()
            denied = malformed = restricted = False
            try:
                client.request("stop")
            except CAEError as exc:
                denied = exc.code == "access_denied"
            try:
                client.request("status", app="admin")
            except CAEError as exc:
                malformed = exc.code == "invalid_protocol"
            try:
                client.request("chat", provider="lab", model="lab-model", text="test")
            except CAEError as exc:
                restricted = exc.code == "access_denied"
            routing = None
            if os.environ.get("CAE_LAB_ROUTING") == "1":
                routing = client.request("route", contract_version=1, capability="chat_generation",
                    model="route-model", input="synthetic", routing_mode="LOCAL_ONLY")
                assert client.request("capabilities")["capabilities"]
            temporary = Path(str(output) + ".new")
            temporary.write_text(json.dumps({"status": status, "models": models,
                "capabilities": capabilities, "routing": routing, "denied": denied, "malformed": malformed,
                "restricted": restricted, "client_pid": os.getpid()}), encoding="utf-8")
            temporary.replace(output)
        except (CAEError, PermissionError):
            pass  # No replay; the next loop is a new read-only request.
        time.sleep(0.5)


if __name__ == "__main__":
    main()
