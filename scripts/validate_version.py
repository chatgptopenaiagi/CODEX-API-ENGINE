import ast
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
module = ast.parse((ROOT / "src/cae/version.py").read_text())
version = ast.literal_eval(module.body[0].value)
if metadata["project"]["version"] != version:
    raise SystemExit("Version validation: FAILED")
print("Version validation: SUCCESS")
