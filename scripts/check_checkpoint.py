"""Read-only validation of source-continuity references; no credentials required."""

import json
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    checkpoint = json.loads((ROOT / "docs/continuity/CAE_CHECKPOINT.json").read_text())
    assert checkpoint["schema_version"] == 1
    assert checkpoint["repository"] == "https://github.com/chatgptopenaiagi/CODEX-API-ENGINE"
    assert checkpoint["development_branch"] == "feat/security-registry"
    assert checkpoint["development_version"] == tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    subprocess.run(["git", "merge-base", "--is-ancestor", checkpoint["latest_verified_source_commit"], "HEAD"], cwd=ROOT, check=True)
    for tag in checkpoint["published_releases"]:
        subprocess.run(["git", "rev-parse", "--verify", "refs/tags/" + tag], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    for name in checkpoint["validation_reports"]:
        path = ROOT / name
        assert path.resolve().is_relative_to(ROOT) and path.is_file()
    for name in ("NEXT_SESSION.md", "MILESTONE_HISTORY_M0_M7.md", "MASTER_ROADMAP_M0_M7.md", "START_NEXT_CODEX_SESSION.md"):
        assert (ROOT / "docs/continuity" / name).is_file()
    assert "NEXT_SESSION.md" in (ROOT / "AGENTS.md").read_text()
    print("Checkpoint references/version/history: PASS; local-only artifacts are not recovery prerequisites.")


if __name__ == "__main__":
    main()
