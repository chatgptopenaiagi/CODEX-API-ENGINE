"""Inspect artifact contents without displaying any file data or secret matches."""

import io
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {"apy_key.txt", ".env", ".env.local"}


def allowed(name: str) -> bool:
    parts = Path(name).parts
    return not any(part.lower() in FORBIDDEN or part.lower().startswith(".env") for part in parts)


def main() -> int:
    failed = False
    archives = 0
    # Compare the exact local source secret in memory when present; never echo it.
    keyfile = ROOT / "apy_key.txt"
    secret = keyfile.read_bytes().strip().removeprefix(b"\xef\xbb\xbf") if keyfile.exists() else b""
    for file in (ROOT / "dist").glob("*"):
        if file.suffix == ".whl":
            archives += 1
            with zipfile.ZipFile(file) as archive:
                for name in archive.namelist():
                    data = archive.read(name)
                    failed |= not allowed(name) or bool(secret and secret in data)
        elif file.name.endswith(".tar.gz"):
            archives += 1
            with tarfile.open(file) as archive:
                for member in archive.getmembers():
                    failed |= not allowed(member.name)
                    if member.isfile():
                        stream = archive.extractfile(member)
                        if stream is not None:
                            failed |= bool(secret and secret in stream.read())
        elif file.suffix == ".exe":
            from PyInstaller.archive.readers import CArchiveReader

            archive = CArchiveReader(str(file))
            for name in archive.toc:
                failed |= not allowed(name)
                data = archive.extract(name)
                failed |= bool(secret and data and secret in data)
                if name.endswith(".pyz"):
                    embedded = archive.open_embedded_archive(name)
                    for module in embedded.toc:
                        failed |= not allowed(module)
                        unpacked = embedded.extract(module, raw=True)
                        failed |= bool(secret and unpacked and secret in unpacked)
                elif name.endswith(".zip") and data:
                    with zipfile.ZipFile(io.BytesIO(data)) as embedded_zip:
                        for member in embedded_zip.namelist():
                            failed |= not allowed(member)
                            failed |= bool(secret and secret in embedded_zip.read(member))
            failed |= bool(secret and secret in file.read_bytes())
    secret = b""
    failed |= archives < 2
    print("Artifact verification: " + ("FAILED" if failed else "SUCCESS"))
    return int(failed)


if __name__ == "__main__":
    try:
        result = main()
    except Exception:
        print("Artifact verification: FAILED")
        result = 1
    raise SystemExit(result)
