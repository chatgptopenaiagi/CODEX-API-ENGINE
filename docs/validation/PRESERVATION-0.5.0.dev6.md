# Experimental development preservation

The explicit preservation mission supersedes M4's earlier completion-dependent
publication policy. Unfinished M4 and absent installer/signing/Windows 11 evidence
do not prevent accurately labeled preservation. Runtime code is frozen at this
mission's starting checkpoint 2a300a0d96a0e8f2ad102940e4a9775d5d256608.
Binaries remain byte-identical to build source 5a0020ca674d157c1213572ac7f7910157805ed5.
No software features are changed or rebuilt in this preservation mission.

Target tag: v0.5.0.dev6-preservation, pointing at the starting source checkpoint.
Status: PUBLISHED_EXPERIMENTAL_PRERELEASE. All 30 remote asset downloads verified.

Redistribution review: see THIRD_PARTY_NOTICES.txt and docs/licenses. No confirmed
prohibition was found for the observed runtime classes; companion notices supply
missing attribution. This is not full legal clearance or an exact transitive SBOM.
Only Microsoft runtime components, not Java classes/runtime code, were pulled from
the JDK directory by PyInstaller. No binary bytes or original archives are changed.

M0–M3: verified development scope. M4 PARTIAL. M5 PLANNED. M6 PARTIAL. M7 PLANNED.
Existing evidence: 421 tests, 96.04%, 18 critical gates, six mock clients, 60 hostile
cases, packaged synthetic recovery and prior M3 real Qwen. These are existing test
results, not a new test run. Current CI must be checked independently.

All existing dev6 artifacts are inventoried with hashes, including prior candidates.
Primary portable/source ZIPs use portable-rc2; older candidates receive preservation
asset-name suffixes to avoid collisions, without changing content. Old blocked labels
inside those archives remain historical. Release-level README and manifests explain
current experimental authorization. No installer is fabricated.

Future agent: read AGENTS.md, docs/continuity/NEXT_SESSION.md, CAE_CHECKPOINT.json,
MILESTONE_HISTORY_M0_M7.md and MASTER_ROADMAP_M0_M7.md. Preserve credentials, running
broker/Qwen, tags and user data. Resume unfinished M4 only with development authority;
this mission itself performs preservation only.

## Preservation checks executed

- `scripts/check_artifacts.py --directory dist/0.5.0.dev6`: PASS, including embedded EXE/PYZ secret exclusion.
- `scripts/audit_publication.py --gitleaks .tmp/gitleaks/gitleaks.exe`: PASS, 203 reviewed eligible files, zero findings.
- Gitleaks Git history, release staging and extracted ZIP content: PASS, zero findings.
- Five existing/new notice ZIP archives: integrity and safe member paths PASS.
- Primary source ZIP: all 189 file members exactly match Git commit 2a300a0.
- All 17 original dev6 artifacts retained unchanged; see committed inventory.
- 90 older local artifact hashes unchanged; v0.2.0/v0.3.1 release IDs, tags,
  descriptions and asset IDs/sizes/digests/update timestamps unchanged.
- Production broker and Qwen process IDs, images and creation times unchanged.
- Existing source checkpoint CI: runs 38210266645 and 38210269683 SUCCESS.
- Original third-party license text retains upstream whitespace; `git diff --check`
  flags that formatting. It was intentionally not rewritten. No code quality gate was lowered.
- No source regression suite rerun or rebuild: runtime, tests, scripts and version
  are unchanged during this preservation mission. Prior results remain historical.

Publication asset names distinguish older portable-candidate archives from the
recommended portable-rc2 bytes. Original checksum/manifests are uploaded under
unique names; release-level manifests/checksums cover the published filenames.
No executable signing, installer, automatic provisioning, Windows 11 certification,
full license certification or POK adapter is claimed.

## Verified GitHub preservation

Release: https://github.com/chatgptopenaiagi/CODEX-API-ENGINE/releases/tag/v0.5.0.dev6-preservation

Tag resolves to 2a300a0d96a0e8f2ad102940e4a9775d5d256608; prerelease=true,
draft=false. Latest stable remains v0.3.1. All 30 uploaded asset sizes match and
all 30 downloaded SHA-256 digests match local staging. Downloaded ZIPs/wheel open
and pass integrity checks. An additional unauthenticated public Control Center
EXE download matches. No existing dev6 artifact was excluded or rebuilt.

Four EXEs, wheel, sdist, primary portable/source ZIPs, older candidate portable/source
ZIPs, original manifests/checksums, current SHA256SUMS.json/txt, RELEASE_MANIFEST.json,
DEVELOPMENT_RECOVERY.json, LICENSE-NOTICES.zip, notices, README-FIRST, validation
reports and M0-M7 roadmap/history are published. No installer exists to upload.
The release's bundled report is the immutable preparation snapshot; this committed
report records subsequent verified results. No uploaded bytes were replaced.

The source archive exactly preserves the release revision. The development branch
also holds later preservation-only documentation/notices. Resolve the final
checkpoint using `git log -1 --format=%H -- docs/continuity` and verify the remote;
no document can embed its own Git commit hash without changing that hash.
No source/features/tests/build scripts/version changed relative to mission start.
Five original unknown untracked user files remain untracked and untouched.

Recovery command: clone the canonical repository into a NEW empty directory,
`git switch --track origin/feat/security-registry`, read AGENTS.md then
NEXT_SESSION.md and CAE_CHECKPOINT.json, run `scripts/resume-development.ps1`
and `python scripts/check_checkpoint.py`. Use Python >=3.14 and the existing
RECOVERY_PROCEDURE.md for dependencies/tests/builds. Production keys are unnecessary.

Independent GitHub recovery PASS at 137596d9dfb1955df3440a4eaeb4f7cf2ceb292c:
fresh clone, clean working tree, correct branch/version, read-only resume script and
checkpoint validator passed. AGENTS, next-session, machine checkpoint, M0-M7 history,
roadmap and recovery procedure were read from that checkout. The release reference
and unfinished M4 task are present. No protected key, private state, repository venv
or prior conversation is required. Final documentation-only follow-up is fetched
and the checkpoint validator repeated before the final report.
