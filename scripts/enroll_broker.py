"""Explicit local enrollment. Writes metadata/configuration only; never accesses a vault."""

import argparse
import json
import os
from pathlib import Path

from cae.pipe_transport import digest, process_peer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    directory = args.directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    # Never silently replace an operator's enrollment or policy.
    if any((directory / name).exists() for name in ("broker.json", "runtime.toml", "client.json")):
        raise SystemExit("Enrollment files already exist; review them explicitly.")
    artifacts = args.artifacts.resolve()
    identities = []
    for app, filename in (("console-client", "CAE-Console-Client.exe"),
                          ("desktop-client", "CAE-Desktop-Client.exe")):
        image = artifacts / filename
        identities.append({"app": app, "image": str(image), "sha256": digest(image)})
    peer = process_peer(os.getpid())
    identities.append({"app": "broker-admin", "image": peer.image,
                       "sha256": peer.sha256, "admin": True})
    server = artifacts / "CAE-Broker.exe"
    server_identity = {"app": "broker", "image": str(server), "sha256": digest(server)}
    pipe = "cae-broker-" + peer.sid.rsplit("-", 1)[-1]
    manifest = {"version": 1, "pipe": pipe, "runtime": str(directory / "runtime.toml"),
                "server": server_identity, "clients": identities}
    policy = 'schema_version = 1\n[[providers]]\nname = "openai"\nkind = "openai"\n'
    for identity in identities:
        policy += (f'\n[[rules]]\nid = "{identity["app"]}-read"\napp = "{identity["app"]}"\n'
                   'provider = "openai"\nprofile = "default"\n'
                   'operations = ["diagnostics", "health", "models", "usage"]\n'
                   'max_requests_per_day = 100\n')
    (directory / "runtime.toml").write_text(policy, encoding="utf-8")
    (directory / "broker.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (directory / "client.json").write_text(json.dumps({"pipe": pipe,
        "server_image": str(server), "server_sha256": server_identity["sha256"]}, indent=2),
        encoding="utf-8")
    print("Local broker enrollment created; no credentials accessed or changed.")


if __name__ == "__main__":
    main()
