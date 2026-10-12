import tomllib
from pathlib import Path

from cae import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_version_and_package_allowlist():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert metadata["project"]["version"] == __version__ == "0.5.0.dev6"
    assert metadata["tool"]["setuptools"]["packages"]["find"]["where"] == ["src"]
    assert (ROOT / "src/cae/py.typed").is_file()


def test_key_excluded():
    assert "apy_key.txt" in (ROOT / ".gitignore").read_text().splitlines()
    assert "global-exclude apy_key.txt" in (ROOT / "MANIFEST.in").read_text()


def test_required_layout():
    for folder in (
        "docs",
        "src",
        "tests",
        "examples",
        "scripts",
        "build",
        "sdk",
        "gui",
        "broker",
        "security",
        "api",
        "credential",
        "tools",
    ):
        assert (ROOT / folder).is_dir()
