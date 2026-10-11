"""Read-only integrity checks for existing distribution files. Never rebuilds."""

import hashlib
import json
import tarfile
import tomllib
import types
import zipfile
from email.parser import BytesParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
ASSETS = (
    "CAE-Control-Center.exe",
    f"codex_api_engine-{VERSION}-py3-none-any.whl",
    f"codex_api_engine-{VERSION}.tar.gz",
    "CAE-Broker.exe",
    "CAE-Console-Client.exe",
    "CAE-Desktop-Client.exe",
)


def code_identity(code: types.CodeType) -> tuple:
    """Compare executable code while ignoring build-machine source filenames."""
    return (
        code.co_code,
        tuple(code_identity(c) if isinstance(c, types.CodeType) else c for c in code.co_consts),
        code.co_names,
        code.co_varnames,
        code.co_freevars,
        code.co_cellvars,
        code.co_argcount,
        code.co_posonlyargcount,
        code.co_kwonlyargcount,
        code.co_flags,
        code.co_exceptiontable,
    )


def main() -> None:
    dist = ROOT / "dist" / VERSION
    checksums = json.loads((dist / "SHA256SUMS.json").read_text(encoding="utf-8-sig"))
    expected = {row["File"]: row["Hash"].lower() for row in checksums}
    assert set(expected) == set(ASSETS)
    for name in ASSETS:
        data = (dist / name).read_bytes()
        assert data and hashlib.sha256(data).hexdigest() == expected[name]
    with zipfile.ZipFile(dist / ASSETS[1]) as archive:
        metadata = BytesParser().parsebytes(
            archive.read(f"codex_api_engine-{VERSION}.dist-info/METADATA")
        )
        assert metadata["Version"] == VERSION
        assert metadata["Name"] == "codex-api-engine"
        for path in (ROOT / "src/cae").glob("*.py"):
            assert archive.read("cae/" + path.name) == path.read_bytes()
    with tarfile.open(dist / ASSETS[2]) as archive:
        for path in (ROOT / "src/cae").glob("*.py"):
            stream = archive.extractfile(f"codex_api_engine-{VERSION}/src/cae/" + path.name)
            assert stream is not None and stream.read() == path.read_bytes()
    from PyInstaller.archive.readers import CArchiveReader

    for asset in ASSETS:
        if not asset.endswith(".exe"):
            continue
        executable = CArchiveReader(str(dist / asset))
        embedded = executable.open_embedded_archive("PYZ.pyz")
        for name in embedded.toc:
            if name == "cae" or name.startswith("cae."):
                relative = name.replace(".", "/")
                path = ROOT / "src" / (relative + ".py")
                if not path.is_file():
                    path = ROOT / "src" / relative / "__init__.py"
                packaged = embedded.extract(name)
                source = compile(path.read_bytes(), str(path), "exec", dont_inherit=True)
                assert code_identity(packaged) == code_identity(source)
    print("Existing release integrity and runtime-source match: SUCCESS")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("Existing release integrity and runtime-source match: FAILED")
        raise SystemExit(1) from None
