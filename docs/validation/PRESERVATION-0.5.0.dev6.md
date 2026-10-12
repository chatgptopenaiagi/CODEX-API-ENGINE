# Experimental development preservation

The explicit preservation mission supersedes M4's earlier completion-dependent
publication policy. Unfinished M4 and absent installer/signing/Windows 11 evidence
do not prevent accurately labeled preservation. Runtime code is frozen at this
mission's starting checkpoint 2a300a0d96a0e8f2ad102940e4a9775d5d256608.
Binaries remain byte-identical to build source 5a0020ca674d157c1213572ac7f7910157805ed5.
No software features are changed or rebuilt in this preservation mission.

Target tag: v0.5.0.dev6-preservation, pointing at the starting source checkpoint.
Status at this preparation commit: PUBLICATION_PENDING, not yet verified remotely.
The next evidence update records actual release/download results.

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
