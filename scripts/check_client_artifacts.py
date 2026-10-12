"""Verify client packages without displaying credentials or archive contents."""

import hashlib
import io
import json
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "dist/0.4.0-clients"
FORBIDDEN = {"apy_key.txt", ".env", ".cae", "broker.json", "client.json", "runtime.toml"}


def main() -> None:
    # Authorized artifact check: compare in memory only; never emit the value or its hash.
    protected = ROOT / "apy_key.txt"
    secret = protected.read_bytes().strip().removeprefix(b"\xef\xbb\xbf") if protected.exists() else b""
    matches: list[str] = []
    scanned = 0

    def inspect(name: str, data: bytes, depth: int = 0) -> None:
        nonlocal scanned
        scanned += 1
        forbidden = any(part.lower() in FORBIDDEN or part.lower().startswith(".env")
                        for part in Path(name).parts)
        encoded = secret.decode("utf-8").encode("utf-16-le") if secret else b""
        if forbidden or (secret and (secret in data or encoded in data)):
            matches.append(name)
        if depth > 4:
            raise ValueError("archive_depth_exceeded")
        if name.endswith((".whl", ".nupkg", ".zip")):
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                assert archive.testzip() is None
                for item in archive.infolist():
                    if not item.is_dir():
                        assert item.file_size < 100_000_000
                        inspect(name + "/" + item.filename, archive.read(item), depth + 1)
        if name.endswith((".tar.gz", ".tgz")):
            with tarfile.open(fileobj=io.BytesIO(data)) as archive:
                for item in archive.getmembers():
                    assert not item.issym() and not item.islnk()
                    if item.isfile():
                        assert item.size < 100_000_000
                        file = archive.extractfile(item)
                        assert file is not None
                        inspect(name + "/" + item.name, file.read(), depth + 1)

    hashes = {}
    for path in sorted(ARTIFACTS.rglob("*")):
        if path.is_file() and path.name not in {"SHA256SUMS.json", "ARTIFACT-VERIFICATION.json"}:
            data = path.read_bytes()
            name = path.relative_to(ARTIFACTS).as_posix()
            assert data, name
            inspect(name, data)
            hashes[name] = hashlib.sha256(data).hexdigest()
    assert not matches, {"unsafe_paths": matches}
    manifest = ROOT / "dist/0.3.1/SHA256SUMS.json"
    for row in json.loads(manifest.read_text()):
        path = manifest.parent / row["File"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["Hash"].lower()
    previous = ROOT / ".tmp/publication031/local-assets.json"
    if previous.exists():
        for name, row in json.loads(previous.read_text()).items():
            path = manifest.parent / name
            assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
    with zipfile.ZipFile(ARTIFACTS / "python/cae_client-0.4.0-py3-none-any.whl") as wheel:
        metadata = wheel.read("cae_client-0.4.0.dist-info/METADATA").decode()
        assert "Version: 0.4.0" in metadata
        assert wheel.read("cae_client/__init__.py") == (ROOT / "clients/python/src/cae_client/__init__.py").read_bytes()
    (ARTIFACTS / "SHA256SUMS.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    result = {"result": "passed", "files_and_archive_members_scanned": scanned,
              "historical_v031_assets_unchanged": True, "credential_matches": 0}
    (ARTIFACTS / "ARTIFACT-VERIFICATION.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
